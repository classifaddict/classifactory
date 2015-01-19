mysql -utree -ptree tree <<EOF
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS app_tree_elementtype_attributes;
DROP TABLE IF EXISTS app_tree_elementtype_required_attr;
DROP TABLE IF EXISTS app_tree_doctype;
DROP TABLE IF EXISTS app_tree_attributetype;
DROP TABLE IF EXISTS app_tree_text;
DROP TABLE IF EXISTS app_tree_attribute;
DROP TABLE IF EXISTS app_tree_elementtype;
DROP TABLE IF EXISTS app_tree_element_texts;
DROP TABLE IF EXISTS app_tree_element_attributes;
DROP TABLE IF EXISTS app_tree_element;
DROP TABLE IF EXISTS app_tree_dataset;
DROP TABLE IF EXISTS app_tree_treenode;
SET FOREIGN_KEY_CHECKS = 1;
EOF
./venv/bin/python project/manage.py syncdb
./venv/bin/python project/manage.py load_xml ipc_scheme 20140101
