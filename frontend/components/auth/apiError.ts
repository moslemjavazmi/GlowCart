export function getApiErrorMessage(error: unknown): string {
  if (!error || typeof error !== "object") {
    return "خطایی رخ داد. لطفاً دوباره تلاش کنید.";
  }

  const apiError = error as {
    status?: number | string;
    data?: unknown;
    error?: string;
  };

  if (typeof apiError.data === "string") {
    return apiError.data;
  }

  if (apiError.data && typeof apiError.data === "object") {
    const data = apiError.data as Record<string, unknown>;

    if (typeof data.detail === "string") {
      return data.detail;
    }

    if (typeof data.message === "string") {
      return data.message;
    }

    const messages = Object.values(data).flatMap((value) => {
      if (typeof value === "string") return [value];

      if (Array.isArray(value)) {
        return value.filter(
          (item): item is string => typeof item === "string"
        );
      }

      return [];
    });

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  if (apiError.status === "FETCH_ERROR") {
    return "ارتباط با سرور برقرار نشد. اتصال اینترنت و اجرای بک‌اند را بررسی کنید.";
  }

  return apiError.error ?? "خطایی رخ داد. لطفاً دوباره تلاش کنید.";
}