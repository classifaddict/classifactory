from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from _diff_trees import diff_trees

class Command(BaseCommand):
    args = ''
    help = 'Diff two trees'

    option_list = BaseCommand.option_list + (
        make_option(
            '--xml',
            action='store_true',
            dest='xml',
            default=False,
            help='Read XML file directly from disk instead from ZIP archive'
        ),
    )

    def handle(self, *args, **options):
        doctype_name = args[0]
        dataset_version1 = args[1]
        dataset_version2 = args[2]
        lang = args[3]

        file_release1 = ''
        file_release2 = ''
        if len(args) == 6:
            file_release1 = args[4]
            file_release2 = args[5]

        diff_trees(
            doctype_name, dataset_version1, dataset_version2, lang,
            file_release1, file_release2,
            xml=options['xml']
        )
