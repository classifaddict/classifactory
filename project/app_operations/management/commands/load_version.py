from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from _ipc2rdf import load

class Command(BaseCommand):
    args = ''
    help = 'Load an IPC Version'

    option_list = BaseCommand.option_list + (
        make_option(
        	'--CPC',
            action='store_true',
            dest='cpc',
            default=False,
            help='Process CPC data'
        ),
    )

    def handle(self, *args, **options):
        cpc = options['cpc']
        load(args[0])
