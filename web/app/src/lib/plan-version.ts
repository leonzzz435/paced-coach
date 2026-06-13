import { DEFAULT_SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS } from "@/lib/generated/version-manifest";

export type SupportedSchemaVersion = (typeof SUPPORTED_SCHEMA_VERSIONS)[number];

export function resolveSchemaVersion(value?: number | null): SupportedSchemaVersion | null {
    if (!value) {
        return null;
    }
    return SUPPORTED_SCHEMA_VERSIONS.includes(value as SupportedSchemaVersion)
        ? (value as SupportedSchemaVersion)
        : null;
}

export { DEFAULT_SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS };
