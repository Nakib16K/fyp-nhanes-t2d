# Application privacy and limitations

Use synthetic examples with this educational demo. Form values are sent to the configured backend to calculate model estimates and explanations. `VITE_API_URL` is public build configuration; it must contain no credential.

The application does not intentionally write prediction inputs to storage or payload logs. API responses use no-store headers, and normal shutdown clears the in-memory model registry. These measures do not prove erasure from browser memory, system buffers, proxies or provider infrastructure.

Local startup uses loopback access and explicit development CORS origins. Production requires configured hosts and HTTPS origins. The hosted preview adds viewer authentication and protected S3/Lambda origins; application validation and CORS alone are not authentication or rate limiting. See [hosting notes](HOSTED_DEMO.md) for its controls and expiry.

The target is a cross-sectional HbA1c/medication-derived survey label. The models do not provide a clinical diagnosis or future-incidence forecast. Percentages are rounded for display; classification flags use full-precision model scores and validation-selected thresholds. SHAP describes one uncalibrated base estimator, not calibrated probability points or causal effects.

Survey weights were not used for national inference. The retained test partition and subgroup uncertainty limit interpretation of the results; see [methodology notes](DISSERTATION_NOTES.md). Small synthetic cloud checks establish sampled technical behaviour, not clinical accuracy or comprehensive security. Cold starts of around 91 seconds remain a usability limitation.

Private data/models, credentials, generated builds and raw runtime records are excluded from the source release. Ignore rules help prevent accidental inclusion but do not remove earlier Git history. The dissertation PDF is not included.
