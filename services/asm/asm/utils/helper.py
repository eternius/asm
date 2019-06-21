from asm.service import Service


def get_service():
    """Return the running asm instance.
    Returns:
        object: asm instance.
    """
    if len(Service.instances) == 1:
        return Service.instances[0]
