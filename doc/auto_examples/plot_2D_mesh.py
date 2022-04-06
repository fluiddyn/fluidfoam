"""
MeshVisu to create vectoriel image of the mesh
=======================================

This example shows how to use MeshVisu object to plot vectorised images
of 2D mesh contained in xy-plane.
"""

###############################################################################
# First create a visualisable mesh object with MeshVisu
# --------------------------------------------------
#
# .. note:: This class allows you to create a list of edge contained inside
#           a box. This list of edges will then be ploted.
#

# import the class MeshVisu
from fluidfoam import MeshVisu

# path to the simulation to load
path = '../fluidfoam/output_samples/pipeline/'

# Load mesh and create an object called myMesh
# The box by default is egal to the mesh dimension
myMesh = MeshVisu( path = '../output_samples/pipeline/')



###############################################################################
# Now plot the the whole mesh
# --------------------------------------------------------------
#

import matplotlib.pyplot as plt
from  matplotlib.collections import LineCollection
import matplotlib.patches as patches

fig, ax = plt.subplots( figsize = (8,8))
# create a collection with edges and print it
ln_coll = LineCollection(myMesh.get_all_edgesInBox(), linewidths = 0.25, colors = 'brown')
ax.add_collection(ln_coll, autolim=True)

# Set box dimensions as the figures's limits
ax.set_xlim(myMesh.get_xlim())
ax.set_ylim(myMesh.get_ylim())

# to avoid distorting the mesh:
ax.set_aspect('equal')

# to don't print axis:
ax.axis('off')

# to save the figure in path (example path = './my_mesh.pdf')
#plt.savefig(path, dpi=fig.dpi, transparent = True, bbox_inches = 'tight')
#plt.show()
#plt.close()


###############################################################################
# Now update the box the zoom on the cylinder
# --------------------------------------------------------------
myMesh.update_box(((0, 0, -1), (0.05, 0.05, 1)))
                    
fig, ax = plt.subplots( figsize = (8,8))
# create a collection with edges and print it
ln_coll = LineCollection(myMesh.get_all_edgesInBox(), linewidths = 0.25, colors = 'black')
ax.add_collection(ln_coll, autolim=True)
#ax.plot([0,1,2,3], [0,10,5,15])
ax.set_xlim(myMesh.get_xlim())
ax.set_ylim(myMesh.get_ylim())
ax.set_aspect('equal')
ax.axis('off')
#plt.savefig("./ma_figure.pdf", dpi=fig.dpi, transparent = True, bbox_inches = 'tight')
#plt.show()
#plt.close()




