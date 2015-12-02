def get_fields_by_name(model_cls, *field_names):
    """Return a dict of `models.Field` instances for named fields.

    Supports wildcard fetches using `'*'`.

        >>> get_fields_by_name(User, 'username', 'password')
        {'username': <django.db.models.fields.CharField: username>,
         'password': <django.db.models.fields.CharField: password>}

        >>> get_fields_by_name(User, '*')
        {'username': <django.db.models.fields.CharField: username>,
         ...,
         'date_joined': <django.db.models.fields.DateTimeField: date_joined>}
    """
    if '*' in field_names:
        return dict((field.name, field) for field in model_cls._meta.fields)
    return dict((field_name, model_cls._meta.get_field(field_name))
                for field_name in field_names)
