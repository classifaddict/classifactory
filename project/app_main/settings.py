"""
Django settings for classifactory project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '8mux_k*i_i2hbp5kqii6ne^v!$ze^^sh$454397ni%np3b5_%l'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mptt',
    'django_mptt_admin',
    'rest_framework',
    'app_operations',
    #'app_scheme',
    'app_tree'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'app_main.urls'

WSGI_APPLICATION = 'app_main.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.sqlite3',
        # 'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        # 'ENGINE': 'django.db.backends.mysql',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'classifactory',
        'USER': 'classifactory',
        'PASSWORD': 'c',
    }
}

try:
    import dj_database_url
    DATABASES['default'] =  dj_database_url.config()
except:
    pass

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Zurich'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

# Dependencies settings

REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS': 'rest_framework.serializers.HyperlinkedModelSerializer',

    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ]
}

# Project settings

DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

DEPTHS = 'stcugm123456789AB'

from string import Template
DOCTYPES = {
    'ipc_scheme': {
        'data_path': Template('ITOS/IPC/data/$version/ipcr_scheme_and_figures'),
        'zip_name': Template('ipcr_scheme_$version$release.zip'),
        'xml_name': Template('ipcr_scheme_$version$release.xml'),
        'root': 'ipcEdition',
        'main_elts': ['revisionPeriods', 'ipcEntry'],
        'remove_elts': ['fr'],
        'main_attrs': ['symbol', 'kind'],
        'skip_attrs': ['edition'],
        'remove_attrs': ['lang', 'ipcLevel', 'priorityOrder', 'documentRoot'],
        'remove_attrs_val': [],
        'mixed_elts': ['text', 'references', 'entryReference'],
        'container_elts': [
            'revisionPeriods', 'revisionPeriod', 'ipcEdition', 'en', 'fr',
            'translation', 'staticIpc', 'ipcEntry', 'textBody', 'note', 'index',
            'title', 'noteParagraph', 'text', 'references', 'subnote', 'orphan',
            'indexEntry', 'titlePart', 'entryReference'
        ]
    },
    'nice_indications': {
        'data_path': Template('ITOS/NICE/data/$version/indications'),
        'zip_name': Template('$version-indications-$release.zip'),
        'xml_name': Template('$version-$lang-indications-$release.xml'),
        'main_elts': ['nice:Indications', 'nice:GoodOrService'],
        'remove_elts': [],
        'main_attrs': ['basicNumber', 'dateInForce'],
        'skip_attrs': [],
        'remove_attrs': ['xsi:schemaLocation'],
        'remove_attrs_val': [],
        'mixed_elts': [
            'nice:Label', 'nice:SortExpression',
            'nice:AlternateSortExpression'
        ],
        'container_elts': [
            'nice:Indications', 'nice:GoodOrService', 'nice:Indication',
            'nice:SynonymIndication', 'nice:Label',
            'nice:SortExpression', 'nice:AlternateSortExpression'
        ]
    },
    'nice_classes': {
        'data_path': Template('ITOS/NICE/data/$version/class_headings_and_explanatory_notes'),
        'zip_name': Template('$version-class_headings_and_explanatory_notes-$release.zip'),
        'xml_name': Template('$version-$lang-class_headings_and_explanatory_notes-$release.xml'),
        'main_elts': ['nice:ClassHeadingsExplanatoryNotes', 'nice:Class'],
        'remove_elts': [],
        'main_attrs': ['classNumber', 'dateInForce'],
        'skip_attrs': [],
        'remove_attrs': ['xsi:schemaLocation'],
        'remove_attrs_val': [],
        'mixed_elts': [
            'nice:HeadingItem', 'nice:Introduction',
            'nice:Include', 'nice:Exclude'
        ],
        'container_elts': [
            'nice:ClassHeadingsExplanatoryNotes', 'nice:Class', 'nice:ClassHeading',
            'nice:ExplanatoryNote', 'nice:IncludesInParticular',
            'nice:ExcludesInParticular', 'nice:HeadingItem',
            'nice:Introduction', 'nice:Include', 'nice:Exclude'
        ]
    }
}
