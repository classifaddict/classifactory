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
EOF
./venv/bin/python project/manage.py syncdb
echo 'Loading ipc_scheme 20170101...'
./venv/bin/python project/manage.py load_xml ipc_scheme 20170101 en --xml
echo
echo 'Loading ipc_scheme 20160101...'
./venv/bin/python project/manage.py load_xml ipc_scheme 20160101 en --xml --no_types
echo
echo 'Diffing ipc_scheme 20160101 and 20170101...'
./venv/bin/python project/manage.py diff_trees ipc_scheme 20160101 20170101
