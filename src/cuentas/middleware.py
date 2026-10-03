from django.contrib.auth import SESSION_KEY


class CerrarSesionInvalidaMiddleware:
    """Cierra en el servidor la sesión cuyo usuario ya no es válido (desactivado o inexistente).

    AuthenticationMiddleware ya trata a ese usuario como anónimo; aquí además se borra la sesión
    (`flush`), de modo que la cookie anterior no sirva aunque el usuario se reactive después.
    Debe ir después de AuthenticationMiddleware y antes de LoginRequiredMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if SESSION_KEY in request.session and not request.user.is_authenticated:
            request.session.flush()
        return self.get_response(request)
