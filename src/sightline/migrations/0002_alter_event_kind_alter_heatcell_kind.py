###############
# Qiyas Sadıqov CC
###############

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sightline', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='kind',
            field=models.CharField(choices=[('click', 'Click'), ('move', 'Pointer move'), ('scroll', 'Scroll'), ('rage', 'Rage click'), ('dead', 'Dead click'), ('input', 'Typing'), ('resize', 'Resize'), ('overlay', 'Overlay shown or hidden'), ('error', 'Script error'), ('custom', 'Custom')], db_index=True, max_length=10),
        ),
        migrations.AlterField(
            model_name='heatcell',
            name='kind',
            field=models.CharField(choices=[('click', 'Click'), ('move', 'Pointer move'), ('scroll', 'Scroll'), ('rage', 'Rage click'), ('dead', 'Dead click'), ('input', 'Typing'), ('resize', 'Resize'), ('overlay', 'Overlay shown or hidden'), ('error', 'Script error'), ('custom', 'Custom')], max_length=10),
        ),
    ]
