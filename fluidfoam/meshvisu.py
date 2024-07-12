"""Visualisation of 2D OpenFoam Mesh with Python
================================================
This module provides functions to read 2D OpenFoam Mesh:

.. autoclass:: MeshVisu

.. automethod:: MeshVisu.get_xlim

.. automethod:: MeshVisu.get_ylim

.. automethod:: MeshVisu.get_zlim

.. automethod:: MeshVisu.get_all_edgesInBox

.. automethod:: MeshVisu.update_box

.. automethod:: MeshVisu.get_box

.. automethod:: MeshVisu.set_box_to_mesh_size

"""

from fluidfoam import OpenFoamFile
import os
import numpy as np

class MeshVisu(object):
    """
    Read OpenFoam mesh of 2D planar simulation and
    list all the edges contained in a box.

    Args:
        path: str\n
        box:  tuple of box's dimension: ((xmin, ymin, zmin), (xmax, ymax, zmax))\n
               (if None, includes the whole mesh)\n
        plane: str  plane in which the mesh is contained, either:\n
               'xy': the xy-plane of outgoing normal z (default value)\n
               'xz': the xz-plane of outgoing normal -y\n
               'yz': the yz-plane of outgoing normal x \n
        time_name: str ('latestTime' is supported)\n
        verbose : True or False (default: True)\n

    A way you might use me is:
        MyMesh = fluidfoam.MeshVisu(path = 'path_of_OpenFoam_case')\n
        
    Then a minimal example to generate and save vectorial mesh figure could be:
        import matplotlib.pyplot as plt\n
        from  matplotlib.collections import LineCollection\n
        fig, ax = plt.subplots()\n
        ln_coll = LineCollection(MyMesh.get_all_edgesInBox())\n
        ax.add_collection(ln_coll, autolim=True)\n
        plt.savefig('./myMesh.svg', dpi=fig.dpi, transparent = True, bbox_inches = 'tight')\n
    """
    def __init__(
        self,
        path,
        box = None,
        plane = 'xy',
        time_name = None,
        verbose = True,
        ):
        """ by_default we expect the 2D mesh to be in xy-plane: """
        # Step 1: read point and face files:
        # read faces in path/constant/polyMesh/
        self.__facefile = OpenFoamFile(
            path = os.path.join(path, 'constant/polyMesh'), 
            name = "faces", 
            verbose = verbose
            )
        
        # if a time_name is given, read points in path/[time_name]/polyMesh/points
        if time_name != None:
            self.__pointfile = OpenFoamFile(
                 path = path,
                 time_name = time_name,
                 name = 'polyMesh/points',
                 verbose = verbose
                )
        # else, just read the constant/polyMesh/points file
        else:
            self.__pointfile = OpenFoamFile(
                path = os.path.join(path, 'constant/polyMesh'), name = "points", verbose = verbose
                )
             
        # Step 2: Define box. Only edges inside the box will be plot.
        if box != None:
           # box = ((xmin, ymin, zmin), (xmax, ymax, zmax)) 
            if len(box[0]) != 3 or len(box[1]) != 3:
                raise ValueError("box mins and maxs must be float tuples of lenght 3")
            self.__box = box
        else:
            # if no box is given, the default size is the whole mesh
            self.set_box_to_mesh_size(verbose=verbose)
          
        # Step 3: list edges in box
        self.__plane = plane
        self._set_edges_in_box(verbose = verbose)
        
            
    def update_box(self, box, verbose = True):
        """ updates the mesh visualization box
        
        Args:
            box: tuple ((xmin, ymin, zmin), (xmax, ymax, zmax))

        A way you might use me is:\n
            MyMesh.update(box = ((0, 0, -1), (0.05, 0.05, 1)))
        
         """
        if len(box[0]) != 3 or len(box[1]) != 3:
            raise ValueError("box mins and maxs must be float tuples of lenght 3")
        self.__box = box
        # update egdes in box
        self._set_edges_in_box(verbose = verbose)
        
    def get_box(self):
        """ return the mesh visualization box 
        
        Returns:
            tuple: ((xmin, ymin, zmin), (xmax, ymax, zmax))"""
        return self.__box
    
    def get_xlim(self):
        """ returns the x limits of the mesh visualization box.
        
        Returns:
            tuple of floats: (xmin, xmax)
        """
        return (self.__box[0][0], self.__box[1][0])
                
    def get_ylim(self):
        """ returns the y limits of the mesh visualization box.
        
        Returns:
            tuple of floats: (ymin, ymax)
        """
        return (self.__box[0][1], self.__box[1][1])
        
    def get_zlim(self):
        """ returns the z limits of the mesh visualization box.
        
        Returns:
            tuple of floats: (zmin, zmax)
        """
        return (self.__box[0][2], self.__box[1][2])
    
    def set_box_to_mesh_size(self, verbose=False):
        """ Set the mesh visualization box to mesh size.
        """
        minx = np.min(self.__pointfile.values_x)
        miny = np.min(self.__pointfile.values_y)
        minz = np.min(self.__pointfile.values_z)
        maxx = np.max(self.__pointfile.values_x)
        maxy = np.max(self.__pointfile.values_y)
        maxz = np.max(self.__pointfile.values_z)
        self.__box = ((minx, miny, minz), (maxx, maxy, maxz))
        if verbose:
            print(f"Box set to mesh size: \n (minx, miny, minz) = {self.__box[0]} \
                \n (maxx, maxy, maxz) = {self.__box[1]}")
        
        
    def _set_edges_in_box(self,  verbose=False):
        """
        create edgesInBox, a list of edges. 
        Eatch edge is in the form ((x0, y0), (x1, y1)) (if mesh contain in 'xy' plane)
        """
        nfaces = self.__facefile.nfaces
        plane = self.__plane
        
        # It is assumed that the mesh is 2D-planar.
        # So there is just 1 cell in the third direction,
        # therefore only 2 possibles values for the points coordonates
        # in this 3rd dimension.
        # example: if plane == 'xy', the  3rd dimension is z.
        #          the points have 2 possible coordinates according to z,
        #          let us call them z0 and z1. 
        #          To avoid unnecessary duplication when displaying, 
        #          we only list the segments belonging to z0.
        
        self._set_plane_coord(plane = plane)
        plane_coord = self._get_plane_coord()
        tmp_id_edges = set() # set that will contain tuples of int which are
                           # index of points in __pointfile.values_z array
        
        # Read box:
        box = self.get_box()       
              
        for i in range(nfaces):
            face = self._get_face(i)
            # First, we check if the face belong to z0 plane:
            if self._is_face_in_plane(face, plane, plane_coord):
                # A face is defined by a list of point indice.
                # two successive points is such a list are connected by an edge,
                # as well as the last and the first point:
                for j, k in zip(face["id_pts"], np.concatenate((face["id_pts"][1:], [face["id_pts"][0]]))):
                    # inside the domain, eatch edges belongs to 2 z0-plane's faces.
                    # we don't want to add 2 times the same edge in __edgesInBox.
                    # tmp_id_edges is a set, so if you try to add an element that
                    # it already contains, that element will not be added
                    if self._is_point_in_box(j, box) or self._is_point_in_box(k, box):
                        # we add tuple of index in ascending order
                        if j < k:
                            tmp_id_edges.add((j, k))
                        else:
                            tmp_id_edges.add((k, j))
        
        # we transform set into list to make __edgesInBox a subscriptable object
        tmp_id_edges = list(tmp_id_edges)
        
        # __edgesInBox will be a list of edges. 
        # Eatch edge is in the form ((x0, y0), (x1, y1))
        self.__edgesInBox = []
        if plane == 'xy':
            for (i, j) in tmp_id_edges:
                x0, y0 = self.__pointfile.values_x[i],  self.__pointfile.values_y[i]
                x1, y1 = self.__pointfile.values_x[j],  self.__pointfile.values_y[j]
                self.__edgesInBox.append(((x0, y0), (x1, y1)))  
        elif plane == 'xz':
            for (i, j) in tmp_id_edges:
                x0, z0 = self.__pointfile.values_x[i],  self.__pointfile.values_z[i]
                x1, z1 = self.__pointfile.values_x[j],  self.__pointfile.values_z[j]
                self.__edgesInBox.append(((x0, z0), (x1, z1)))
        elif plane == 'yz':
            for (i, j) in tmp_id_edges:
                y0, z0 = self.__pointfile.values_y[i],  self.__pointfile.values_z[i]
                y1, z1 = self.__pointfile.values_y[j],  self.__pointfile.values_z[j]
                self.__edgesInBox.append(((y0, z0), (y1, z1)))    
            
    
    def get_all_edgesInBox(self):
        """ 
         return the list of all edges in box. \n
         Eatch edge is describe by a tuple of tuples of float: ((x0, y0), (x1, y1)). \n
         (x0, y0) being the coordonates of the fisrt point, (x1, y1), the 
         coordinates of the second point. \n
         This list can be given as an argument to the matplotlib LineCollection 
         function, which allows to display a large number of segments on an image.
        
        Returns:
            list of tuples
        """
        return (self.__edgesInBox)
        
    def _set_plane_coord(self, plane):
        """we assume mesh is 2D planar. Therefore there is only 
        one cell in the third direction (normal to mesh), so the 3rd coordinates 
        of the mesh points have only two possible values. We choose one of them 
        arbitrarily, named it __plane_coord. \n
        We will only draw the segments belonging to the plane at __plane_coord.
        """
        if plane == 'xy':
            self.__plane_coord = self.__pointfile.values_z[0]
        elif plane == 'xz':
            self.__plane_coord = self.__pointfile.values_y[0]
        elif plane == 'yz':
            self.__plane_coord = self.__pointfile.values_x[0]
        else:
            print(f"plane={plane} but must be str egals to 'xy', 'xz' or 'yz'")
        
    def _get_plane_coord(self):
        """we assume mesh is 2D planar,
         return the plan coordonate in normal direction"""
        return self.__plane_coord
    
    def _get_face(self, i):
        """ get the dictionnary describing the face i """
        return (self.__facefile.faces[i])
    
    def _is_point_in_box(self, i, box):
        """ return a booleen, True if the point of indice i in inside 
        the box, False otherwise.
        """
        x = self.__pointfile.values_x[i]
        y = self.__pointfile.values_y[i]
        z = self.__pointfile.values_z[i]
        # box[0] = (xmin, ymin, zmin)
        # box[1] = (xmax, ymax, zmax)
        if box[0][0] > x or box[1][0] < x:
            return False
        elif box[0][1] > y or box[1][1] < y:
            return False
        elif box[0][2] > z or box[1][2] < z:
            return False
        else:
            return True
            
    def _is_face_in_plane(self, face, plane, plane_coord):
        """
        check if all points of the face belong to the plane
        """
        if plane == 'xy':
            for j in range(face["npts"]):
                if self.__pointfile.values_z[j] != plane_coord:
                    return False
                    
        elif plane == 'xz':
            for j in range(face["npts"]):
                if self.__pointfile.values_y[j] != plane_coord:
                    return False
                    
        elif plane == 'yz':
            for j in range(face["npts"]):
                if self.__pointfile.values_x[j] != plane_coord:
                    return False
        
        return True
