use std::sync::Arc;

use codex_config::Config;
use codex_features::Feature;
use codex_login::{
    AuthManager,
    auth::{AgentIdentityAuthPolicy, AuthKeyringBackendKind},
};
use codex_model_provider::ProviderAuthContext;
use codex_protocol::{ThreadId, openai_models::ModelInfo, protocol::SessionSource};

use crate::{client::ModelClient, session::session::Session};

use super::build_models_manager;

/// Builds the isolated client used by VL background tasks.
///
/// The client uses the configured local credentials and model provider, but does
/// not inherit a thread-scoped runtime-auth owner. Its model metadata is resolved
/// through the same catalog path as foreground sessions.
pub async fn build_background_model_client(
    config: &Config,
    model_name: &str,
    session_source: SessionSource,
) -> (ModelClient, ModelInfo) {
    let auth_manager = Arc::new(
        AuthManager::new(
            config.codex_home.to_path_buf(),
            /*enable_codex_api_key_env*/ false,
            config.cli_auth_credentials_store_mode,
            /*forced_chatgpt_workspace_id*/ None,
            Some(config.chatgpt_base_url.clone()),
            AuthKeyringBackendKind::default(),
            config.auth_route_config(),
        )
        .await,
    );

    let models_manager = build_models_manager(config, Arc::clone(&auth_manager), None);
    let model_info = models_manager
        .get_model_info(model_name, &config.to_models_manager_config())
        .await;

    let provider = ProviderAuthContext {
        credentials: auth_manager,
        runtime_auth: None,
    }
    .model_provider(config.model_provider.clone());

    let client = ModelClient::new(
        provider,
        if config.features.enabled(Feature::UseAgentIdentity) {
            AgentIdentityAuthPolicy::ChatGptAuth
        } else {
            AgentIdentityAuthPolicy::JwtOnly
        },
        ThreadId::new(),
        Session::new_item_id_generator(),
        session_source,
        codex_utils_cli::originator().value,
        config.model_verbosity,
        config.features.enabled(Feature::ContentItemKinds),
        /*reasoning_effort_override_enabled*/ false,
        config.features.enabled(Feature::EnableRequestCompression),
        config.features.enabled(Feature::RuntimeMetrics),
        /*beta_features_header*/ None,
        /*concurrent_reasoning_summaries_enabled*/ false,
        /*output_token_replay_enabled*/ false,
        /*attestation_provider*/ None,
        config.http_client_factory(),
        config.workspace_routing_context(),
        Vec::new(),
    );

    (client, model_info)
}
