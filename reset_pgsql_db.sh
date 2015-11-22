psql -q classifactory classifactory <<EOF
DROP TABLE app_tree_elementtype_attributes CASCADE;
DROP TABLE app_tree_elementtype_required_attr CASCADE;
DROP TABLE app_tree_doctype CASCADE;
DROP TABLE app_tree_attributetype CASCADE;
DROP TABLE app_tree_text CASCADE;
DROP TABLE app_tree_attribute CASCADE;
DROP TABLE app_tree_elementtype CASCADE;
DROP TABLE app_tree_element_texts CASCADE;
DROP TABLE app_tree_element_attributes CASCADE;
DROP TABLE app_tree_element CASCADE;
DROP TABLE app_tree_dataset CASCADE;
DROP TABLE app_tree_diff CASCADE;
DROP TABLE app_tree_treenode CASCADE;
DROP TABLE app_tree_translation CASCADE;
DROP TABLE app_scheme_concept CASCADE;
DROP TABLE app_scheme_definition CASCADE;
DROP TABLE app_scheme_reference CASCADE;
DROP TABLE django_admin_log CASCADE;
DROP TABLE django_content_type CASCADE;
DROP TABLE django_migrations CASCADE;
DROP TABLE django_session CASCADE;
DROP TABLE auth_group CASCADE;
DROP TABLE auth_group_permissions CASCADE;
DROP TABLE auth_permission CASCADE;
DROP TABLE auth_user CASCADE;
DROP TABLE auth_user_groups CASCADE;
DROP TABLE auth_user_user_permissions CASCADE;
EOF
./venv/bin/python project/manage.py migrate

echo 'Loading ipc_scheme 20170101...'
./venv/bin/python -m cProfile -o load.stats project/manage.py load_xml ipc_scheme 20170101 en --xml
./venv/bin/gprof2dot -f pstats load.stats | dot -Tpng -o load1.png
echo

echo 'Loading ipc_scheme 20160101...'
./venv/bin/python -m cProfile -o load.stats project/manage.py load_xml ipc_scheme 20160101 en --xml --no_types
./venv/bin/gprof2dot -f pstats load.stats | dot -Tpng -o load2.png

echo
echo 'Diffing ipc_scheme 20160101 and 20170101...'
./venv/bin/python project/manage.py diff_trees ipc_scheme 20160101 20170101 en --xml
