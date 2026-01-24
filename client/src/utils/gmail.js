export const getGmailReturnTo = () => {
  if (typeof window === "undefined") {
    return "/";
  }
  const { pathname, search } = window.location;
  return `${pathname || ""}${search || ""}`;
};

export const isGmailAuthorized = (status) =>
  Boolean(status?.authorized) || status?.availability === "authorized";

export const consumeGmailRedirectFragment = () => {
  if (typeof window === "undefined") {
    return null;
  }
  const fragment = window.location.hash?.replace("#", "");
  if (!fragment || !fragment.startsWith("gmail_")) {
    return null;
  }
  const nextUrl = `${window.location.pathname}${window.location.search || ""}`;
  window.history.replaceState(null, "", nextUrl);
  return fragment;
};
