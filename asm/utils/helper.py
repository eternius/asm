def get_service():
    """Return the running asm instance.
    Returns:
        object: asm instance.
    """
    from asm.manager.core import Service

    if len(Service.instances) == 1:
        return Service.instances[0]
