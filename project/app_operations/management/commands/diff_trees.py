from django.core.management.base import BaseCommand, CommandError
#from optparse import make_option
from _diff_trees import diff_trees

class Command(BaseCommand):
    args = ''
    help = 'Diff two trees'

    def handle(self, *args, **options):
        diff_trees(*args)
