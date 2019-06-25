def add_service_attributes(func):
    """Add the attributes which makes a function a service.
    Args:
        func (func): Service function.
    Returns:
        func: The module function with the new attributes.
    """
    if not hasattr(func, "service"):
        func.service = True
    if not hasattr(func, "nlp"):
        func.nlp = True
    if not hasattr(func, "matchers"):
        func.matchers = []
    if not hasattr(func, "constraints"):
        func.constraints = []
    return func


def match_event(event_type):
    """Return event type matcher."""

    def matcher(func):
        """Add decorated function to list for event matching."""
        func = add_service_attributes(func)
        func.matchers.append({"event_type": {"type": event_type}})
        return func

    return matcher


def match_webhook(webhook):
    """Return webhook match decorator."""

    def matcher(func):
        """Add decorated function to modules list for webhook matching."""
        func = add_service_attributes(func)
        func.matchers.append({"webhook": webhook})

        return func

    return matcher


def match_setup():
    """Return setup match decorator."""

    def matcher(func):
        """Add decorated function to modules list for setup matching."""
        func = add_service_attributes(func)
        func.matchers.append({"setup": True})

        return func

    return matcher


def match_service(service):
    """Return service match decorator."""

    def matcher(func):
        """Add decorated function to modules list for service matching."""
        func = add_service_attributes(func)
        func.matchers.append({"service_type": service})

        return func

    return matcher


def match_nlp_train():
    """Return nlp_train match decorator."""

    def matcher(func):
        """Add decorated function to modules list for nlp_train matching."""
        func = add_service_attributes(func)
        func.matchers.append({"nlp_train": True})

        return func

    return matcher


def match_parse_text():
    """Return parse_text match decorator."""

    def matcher(func):
        """Add decorated function to modules list for parse_text matching."""
        func = add_service_attributes(func)
        func.matchers.append({"parse_text": True})

        return func

    return matcher


def match_get_response():
    """Return get_response match decorator."""

    def matcher(func):
        """Add decorated function to modules list for get_response matching."""
        func = add_service_attributes(func)
        func.matchers.append({"get_response": True})

        return func

    return matcher


def match_generic_action():
    """Return generic_action match decorator."""

    def matcher(func):
        """Add decorated function to modules list for generic_action matching."""
        func = add_service_attributes(func)
        func.matchers.append({"generic_action": True})

        return func

    return matcher
