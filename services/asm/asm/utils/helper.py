# pylint: disable=inconsistent-return-statements
def get_service():
    """Return the running asm instance.
    Returns:
        object: asm instance.
    """
    from asm.manager import ArcusServiceManager

    if len(ArcusServiceManager.instances) == 1:
        return ArcusServiceManager.instances[0]
