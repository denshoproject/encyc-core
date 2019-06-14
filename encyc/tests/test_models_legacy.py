from bs4 import BeautifulSoup
from deepdiff import DeepDiff
import pytest

from encyc.models import legacy


#FIND_DATABOXCAMPS_COORDS_in0 = """
#Just some random text that contains no coordinates
#"""
#FIND_DATABOXCAMPS_COORDS_in1 = """
#<div id="databox-Camps">
#<p>
#SoSUID: w-tule;
#DenshoName: Tule Lake;
#USGName: Tule Lake Relocation Center;
#GISLat: 41.8833;
#GISLng: -121.3667;
#GISTGNId: 2012922;
#</p>
#</div>
#"""
# 
#def test_find_databoxcamps_coordinates():
#    out0a = (); out0b = []
#    out1a = (-121.3667, 41.8833); out1b = [-121.3667, 41.8833]
#    # TODO test for multiple coordinates on page
#    assert mediawiki.find_databoxcamps_coordinates(
#        FIND_DATABOXCAMPS_COORDS_in0
#    ) in [out0a, out0b]
#    assert mediawiki.find_databoxcamps_coordinates(
#        FIND_DATABOXCAMPS_COORDS_in1
#    ) in [out1a, out1b]
