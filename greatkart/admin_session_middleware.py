ADMIN_SESSION_COOKIE = "adminid"


class AdminSessionMiddleware:
    """Use a separate session cookie for /secureadmin/ URLs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_admin = request.path.startswith("/secureadmin/")
        if is_admin:
            original_cookie = request.COOKIES.get("sessionid")
            admin_cookie = request.COOKIES.get(ADMIN_SESSION_COOKIE)
            # Swap in the admin session cookie
            request.COOKIES["sessionid"] = admin_cookie or ""

        response = self.get_response(request)

        if is_admin:
            # Restore original cookie so store session is untouched
            if original_cookie is not None:
                request.COOKIES["sessionid"] = original_cookie

            # Copy the Set-Cookie sessionid header to adminid
            if "sessionid" in response.cookies:
                morsel = response.cookies["sessionid"]
                response.cookies[ADMIN_SESSION_COOKIE] = morsel.coded_value
                cookie = response.cookies[ADMIN_SESSION_COOKIE]
                cookie["path"] = morsel.get("path", "/")
                cookie["httponly"] = morsel.get("httponly", True)
                cookie["samesite"] = morsel.get("samesite", "Lax")
                del response.cookies["sessionid"]

        return response
