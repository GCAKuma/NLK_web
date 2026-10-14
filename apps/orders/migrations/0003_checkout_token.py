import uuid
from django.db import migrations, models


def fill_tokens(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    for order in Order.objects.using(schema_editor.connection.alias).filter(checkout_token__isnull=True).iterator():
        Order.objects.using(schema_editor.connection.alias).filter(pk=order.pk).update(checkout_token=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [("orders", "0002_alter_order_status_alter_paymentproof_status")]
    operations = [
        migrations.AddField(model_name="order", name="checkout_token", field=models.UUIDField(null=True, editable=False)),
        migrations.RunPython(fill_tokens, migrations.RunPython.noop),
        migrations.AlterField(model_name="order", name="checkout_token", field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
    ]
