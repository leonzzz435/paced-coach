import {
    DEFAULT_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
    SUPPORTED_SCHEMA_VERSIONS_BY_KIND,
} from "@/lib/generated/version-manifest";

export type SupportedSchemaVersion = (typeof SUPPORTED_SCHEMA_VERSIONS)[number];
export type SchemaArtifactKind = keyof typeof SUPPORTED_SCHEMA_VERSIONS_BY_KIND;

export function resolveSchemaVersion(kind: SchemaArtifactKind, value?: number | null): SupportedSchemaVersion | null {
    if (!value) {
        return null;
    }
    const supported = SUPPORTED_SCHEMA_VERSIONS_BY_KIND[kind] as readonly number[];
    return supported.includes(value)
        ? (value as SupportedSchemaVersion)
        : null;
}

export { DEFAULT_SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS, SUPPORTED_SCHEMA_VERSIONS_BY_KIND };
