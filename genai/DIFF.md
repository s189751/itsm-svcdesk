---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0 with opentelemetry-sdk 1.45.0 and openai 3.19.2"
  spec_ref: "semantic-conventions@v1.41.1"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.max_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
---
<!-- ai-generated: 25% - spans captured with the pinned instrumentation, prose mine -->

# What the library emits, against the spec

One instrumented chat completion against an OpenAI-compatible endpoint (a local model), one span `chat <model>`, nine `gen_ai.*` attributes — and every one of them is defined in semantic-conventions v1.41.1 with stability development. The library matches the spec exactly on this call: operation and provider names, request model and max_tokens, response id, model and finish reasons, input and output token counts.

What agrees: the usage pair (gen_ai.usage.input_tokens/output_tokens, 20 in / 2 out for a "say done" prompt) follows the v1.41.1 counting note; finish_reasons carries ["stop"] as a string array as specified; provider reports "openai" for an OpenAI-compatible API. What is missing rather than wrong: the span carries no error attributes (the call succeeded), no streaming attributes (no streaming), and no cost or cache attributes the spec defines for other setups. For a dashboard built on these attributes that means the nine keys above are safe group-by/filter dimensions today, with the caveat that everything here is still development stability: a future spec release may rename them, so dashboards should tolerate absence, not assume presence.
