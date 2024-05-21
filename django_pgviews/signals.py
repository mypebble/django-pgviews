from django.dispatch import Signal

# providing_args removed in Django 4.0, copied here instead:
# view_synced providing_args=['update', 'force', 'status', 'has_changed']
view_synced = Signal()
all_views_synced = Signal()
