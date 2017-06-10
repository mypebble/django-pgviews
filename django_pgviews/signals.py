from django.dispatch import Signal


view_synced = Signal(
    providing_args=['update', 'force', 'status', 'has_changed'])
all_views_synced = Signal()
