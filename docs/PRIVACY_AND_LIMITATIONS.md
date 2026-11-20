# Privacy and limitations

Use synthetic examples. The dashboard sends form values to the configured API to calculate scores and explanations. The application is designed to avoid saving input values or writing them to application logs. Responses request that clients avoid caching them. Browsers, proxies and hosting infrastructure can have their own records and buffers.

The hosted demo requires a shared credential before serving the dashboard or API requests. CloudFront signs requests to private origins. The single-request concurrency limit controls capacity, and the project does not provide individual accounts or per-user rate limits. See [hosting architecture](HOSTING_ARCHITECTURE.md).

The model scores describe an educational comparison using a survey-derived diabetes-status label. Clinical diagnosis and future risk require other evidence. Survey design, earlier use of the test partition and small subgroup counts limit what can be inferred from the results. See [dissertation notes](DISSERTATION_NOTES.md).

The application shows rounded scores and uses the full score for each model's validation threshold. SHAP describes how features contribute to one model's internal score. See [local explanations](LOCAL_EXPLANATIONS.md).
