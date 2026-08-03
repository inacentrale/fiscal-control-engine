from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    provider_name: str
    model_name: str


@dataclass(frozen=True)
class ModelRegistry:
    primary: ModelSpec
    fallbacks: tuple[ModelSpec, ...]

    @classmethod
    def from_chain(cls, provider_chain: str) -> "ModelRegistry":
        raw_entries = [
            entry.strip() for entry in provider_chain.split(",") if entry.strip()
        ]
        if not raw_entries:
            raise ValueError("at least one model is required")
        specs = tuple(_parse_model_spec(entry) for entry in raw_entries)
        return cls(primary=specs[0], fallbacks=specs[1:])


def _parse_model_spec(entry: str) -> ModelSpec:
    if ":" not in entry:
        raise ValueError("model entry must use provider:model format")
    provider_name, model_name = (part.strip() for part in entry.split(":", maxsplit=1))
    if not provider_name or not model_name:
        raise ValueError("model provider and model must be non-empty")
    return ModelSpec(provider_name=provider_name, model_name=model_name)
