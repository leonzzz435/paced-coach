import StravaCompleteClient from "./strava-complete-client";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function getSingleValue(value: string | string[] | undefined): string | null {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value) && typeof value[0] === "string") {
    return value[0];
  }
  return null;
}

export default async function StravaCompletePage({ searchParams }: PageProps) {
  const resolvedSearchParams = (await searchParams) ?? {};
  return (
    <StravaCompleteClient
      connected={getSingleValue(resolvedSearchParams.connected)}
      oauthError={getSingleValue(resolvedSearchParams.oauth_error)}
    />
  );
}
