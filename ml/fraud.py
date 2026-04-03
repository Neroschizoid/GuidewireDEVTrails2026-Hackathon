def check_fraud(is_active, already_paid):
    if not is_active:
        return True
    if already_paid:
        return True
    return False