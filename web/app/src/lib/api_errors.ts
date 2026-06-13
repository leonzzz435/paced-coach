export type ApiError = Error & {
  status?: number;
  bodyText?: string;
};

export function isApiError(err: unknown): err is ApiError {
  if (!(err instanceof Error)) return false;
  return "status" in err;
}

export function apiError(message: string, status?: number, bodyText?: string): ApiError {
  const err = new Error(message) as ApiError;
  if (status !== undefined) err.status = status;
  if (bodyText !== undefined) err.bodyText = bodyText;
  return err;
}

