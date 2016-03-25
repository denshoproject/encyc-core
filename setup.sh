rm     /usr/local/src/encyc-core/encyc/*.pyc
rm -Rf /usr/local/src/encyc-core/encyc_core.egg-info/
rm -Rf /usr/local/src/encyc-core/build/
rm -Rf /usr/local/src/encyc-core/dist/
rm -Rf /usr/local/lib/python2.7/dist-packages/encyc*
rm -Rf /usr/local/src/env/encyc/lib/python2.7/site-packages/encyc*
rm     /usr/local/src/env/encyc/bin/encyc
cd /usr/local/src/encyc-core/
source /usr/local/src/env/encyc/bin/activate
#pip install -U -r requirements/_base.txt
python setup.py install
cd /usr/local/src/encyc-core/
date
