from django.core.management.base import BaseCommand
from optparse import make_option
from _xml_load import load


class Command(BaseCommand):
    help = 'Load an XML File'
    args = '<doctype_name dataset_version [file_release] ...>'

    option_list = BaseCommand.option_list + (
        make_option(
            '--xml',
            action='store_true',
            dest='xml',
            default=False,
            help='Read XML file directly from disk instead from ZIP archive'
        ),
        make_option(
            '--no_types',
            action='store_true',
            dest='no_types',
            default=False,
            help='Do not register element and attribute types'
        ),
    )

    def handle(self, *args, **options):
        doctype_name = args[0]
        dataset_version = args[1]
        file_release = ''
        if len(args) == 3:
            file_release = args[2]
        load(
            doctype_name, dataset_version, file_release,
            no_types=options['no_types'], xml=options['xml']
        )
