from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from _xml_load import load

class Command(BaseCommand):
    args = ''
    help = 'Load an XML File'

    option_list = BaseCommand.option_list + (
        make_option(
        	'--z',
            action='store_true',
            dest='zip',
            default=False,
            help='Read XML file(s) from ZIP archive'
        ),
    )

    def handle(self, *args, **options):
        zip = options['zip']
        load(*args)
