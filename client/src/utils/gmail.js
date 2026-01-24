export const getGmailReturnTo = () => {
  if (typeof window === "undefined") {
    return "/";
  }
  const { pathname, search } = window.location;
  return `${pathname || ""}${search || ""}`;
};

export const isGmailAuthorized = (status) =>
  Boolean(status?.authorized) || status?.availability === "authorized";

export const getSafeReturnTo = (value) => {
  if (!value || typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed || trimmed.startsWith("//")) {
    return null;
  }
  if (/^https?:\/\//i.test(trimmed)) {
    return null;
  }
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
};
