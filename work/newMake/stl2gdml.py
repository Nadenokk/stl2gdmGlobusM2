import ast
import sys
#import numpy as np
from bisect import bisect
import __main__

if int(sys.version_info.major)>=3:
	xrange = range

HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
SCHEMA = '<gdml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="/projects/soft/ext/sources/geant4.10.06.p01/environments/g4py/examples/gdml/GDMLSchema/gdml.xsd">\n'
FOOTER = '</gdml>'


AUNIT  = 'deg'
LUNIT  = 'mm'


MATERIALS_LIST = [
	{"name" : "Vacuum"}, {"name" : "Aluminum"},{"name" : "CarbonFibre"}, {"name" : "Copper"}, {"name" : "Silicon"}, {"name" : "Glass"}, {"name" : "FibrousGlass"}, {"name" : "Q235"},
	{"name" : "Concrete"}, {"name" : "CeramicBrick"}, {"name" : "MineralSlabs"}, {"name" : "Graphite"}, {"name" : "Wood"}, {"name" : "Bitumen"}, {"name" : "RoofingFelt"}, {"name" : "Water"},
	{"name" : "Ground"}, {"name" : "Polietilen"},
]

VACUUM = '''
    <materials>
        <element name="videRef"    formula="VACUUM" Z="1"> <atom value="1."/>       </element>
        <material formula=" " name="Vacuum">
            <D value="1.e-25" unit="g/cm3" />
            <fraction n="1.0" ref="videRef" />
        </material>
    </materials>
'''

WORLD = '''
    <setup name="Default" version="1.0">
        <world ref="%s"/>
    </setup>
'''

STRUCTURE = '''
    <structure>
        <volume name="%s">
            <materialref ref="%s"/>
            <solidref ref="%s"/>%s
        </volume>
    </structure>
'''

MODULE_NAME  = __main__.__file__.split("/")[-1].split("\\")[-1] 
HELP_MESSAGE = ''' 

    Usage: 
            python  %s  out_name  input_file_1.stl input_file_2.stl  input_file_N.stl"

            or

            python  %s  out_name  path_to_stl_file/blah_blah_*.stl


    Materials:
 
            Material are encoded in the stl file name
            For instance, my_geometry_part_Aluminum.stl - this part will be parsed as made of aluminum
            See  %s --materials to display list of available materials
              
	
'''%(MODULE_NAME,MODULE_NAME,MODULE_NAME)






def __is_help__():
	ishelp = False 
	for arg in sys.argv:
		if "-h" in arg.lower() and arg[0]=="-": ishelp = True 
		if "help" in arg.lower(): ishelp = True
	if ishelp: print (HELP_MESSAGE)


def __print_error__(text):
	print (text)


def __print__(text):
	print (text)


def __print_progress_bar__(text,percentage):
	sys.stdout.write("\r%s %5.1f%%"%(text,percentage))
	sys.stdout.flush()
	if percentage==100.: print()


def __print_and_terminate__(text):
	__print_error__(text + " ==> terminating the program!")
	raise SystemExit
	

def __str_to_float__(text):
	try:
		return ast.literal_eval(text)
	except Exception as e:
		__print_and_terminate__("String to float conversion failed due to: "+str(e))

def __float_to_str__(val):
	return '{}'.format(val)
		
def __get_three_values__(line, delimiter):
	vals = line.split(delimiter)[-1]
	vals = vals.split()
	if len(vals)!=3:
		__print_and_terminate__("Input format inconsistency: more than 3 values per line: "+line)
	return [__str_to_float__(val) for val in vals]

def __vectr_subtr__(vector1, vector2):
	return [x[0]-x[1] for x in zip(vector1,vector2)]

def __vector_cross__(vector1, vector2):
	return [
                  vector1[1]*vector2[2] - vector1[2]*vector2[1],
                - vector1[0]*vector2[2] + vector1[2]*vector2[0],
                  vector1[0]*vector2[1] - vector1[1]*vector2[0],
                        ]

def __vector_inner__(vector1,vector2):
	return sum([x[0]*x[1] for x in zip(vector1,vector2)])

def __get_orientation__(norm, v1, v2, v3):
	vec1 = __vectr_subtr__(v2, v1)
	vec2 = __vectr_subtr__(v3, v2)
	norm1 = __vector_cross__(vec1,vec2)
	return 1 if __vector_inner__(norm,norm1)>0 else -1

def __get_inputname_base__(fname):
	return fname.split("/")[-1].split(".stl")[0]


def get_triangles(fname):
	f=open(fname,"r")
	solid = None

	lines  = f.readlines()
	nlines = len(lines)
	for l in xrange(nlines):
		__print_progress_bar__("Processing file     %s: "%fname,100.*(l+1)/nlines)
		line = lines[l].lower()
	

		# start facet 
		if "facet " in line:
			solid = {}

		# Get normal to triangle
		if "normal" in line:
			if "normal" in solid.keys():
				__print_and_terminate__("Input format inconsistency: duplicate normal for triangle")
			solid["normal"] = __get_three_values__(line, "normal")
			continue


		# Get vertices
		if "vertex" in line:
			if "vertex" not in solid:
				solid["vertex"] = []
			if len(solid["vertex"])>=3:
				__print_and_terminate__("Input format inconsistency: more than 3 vertices per triangle")
			solid["vertex"].append(__get_three_values__(line,"vertex"))
			continue


		# Finalize the triangle
		if "endfacet" in line:
			yield solid


def guess_material(fname):
	target = fname.lower()
	materials = [m["name"] for m in MATERIALS_LIST if m["name"].lower() in target]
	if len(materials)>1:
		return MATERIALS_LIST[0]["name"]
	elif not materials:
		return MATERIALS_LIST[0]["name"]
	__print__("    File %s - material parsed: %s"%(fname,materials[0]))
	return materials[0]

def stl_to_gdml(fname):
	outname = __get_inputname_base__(fname)
	outsolidname = outname+"-SOL"

	# sort vertices
	triangles = []
	sortedvertexes = []
	for triangle in get_triangles(fname):
		triangles.append(triangle)
		for vertex in triangle["vertex"]:
			x = __float_to_str__(vertex[0])
			y = __float_to_str__(vertex[1])
			z = __float_to_str__(vertex[2])
			thekey = x+y+z
			sortedvertexes.append(thekey)

	#__print__("Soring vertices - may take some time...")
	sortedvertexes = sorted(sortedvertexes)
	#__print__("... done sorting")

	# remove duplicates from verticves
	previous = None
	sortednoduplicates = []
	vertexidnoduplicates = []
	for tmpvertex in sortedvertexes:
		if tmpvertex == previous: continue
		sortednoduplicates.append(tmpvertex)
		vertexidnoduplicates.append(None)
		previous = tmpvertex
	
	# create gdml vertices
	# create gdml solids
	vertices = '\n    <define>\n'
	solids   = '\n    <solids>\n'
	solids  += '        <tessellated aunit="%s" lunit="%s" name="%s">\n'%(AUNIT,LUNIT,outsolidname)
	vertexid = 0
	for i in xrange(len(triangles)):
		triangle = triangles[i]
		__print_progress_bar__("generating gdml for %s: "%fname,100.*(i+1)/len(triangles))
		if len(triangle["vertex"])!=3:
			__print_and_terminate__("Illegal number of vertices per triangle: "+str(triangle["vertex"]))
		ids = []
		for vertex in triangle["vertex"]:
			x = __float_to_str__(vertex[0])
			y = __float_to_str__(vertex[1])
			z = __float_to_str__(vertex[2])
			thekey = x+y+z
			theitem = bisect(sortednoduplicates, thekey)-1
			assert(theitem>=0)
			# add vertex to gdml
			if vertexidnoduplicates[theitem] is None: 
				vertices+='        <position name="%s_v%d" unit="%s" x="%s" y="%s" z="%s"/>\n'%	(outname, vertexid, LUNIT, x, y, z) 
				vertexidnoduplicates[theitem] = vertexid
				vertexid+=1
			#  add vertex to facet
			ids.append(vertexidnoduplicates[theitem])

		# create facet
		orientation = __get_orientation__(triangle["normal"], *triangle["vertex"])
		idsforsolid = ids if orientation>0 else [ids[2],ids[1],ids[0]]
		solids+= '             <triangular vertex1="%s_v%d" vertex2="%s_v%d" vertex3="%s_v%d"/>\n'%(outname, idsforsolid[0], outname, idsforsolid[1], outname, idsforsolid[2])

	
	# finalize 
	vertices+= '    </define>\n'
	solids+=   '        </tessellated>\n'
	solids+=   '    </solids>\n'

	# material
	material = guess_material(fname) # "Vacuum"

	# structure
	structure = STRUCTURE%(outname, material, outsolidname,"")

	# world
	world = WORLD%outname
	
	# create output gdml file
	outfilename = outname+".gdml"
	fout = open(outfilename,"w")
	fout.write(HEADER)
	fout.write(SCHEMA)
	fout.write(vertices)
	fout.write(VACUUM)
	fout.write(solids)
	fout.write(structure)
	fout.write(world)
	fout.write(FOOTER)
	fout.close()
	return outfilename
					 									

def creat_gdml_bundle(outname, infiles):
	# some world constants
	WORLD_BOX_SIZE = __float_to_str__(10000.)
	SOLIDNMAE  = "world_solid"
	VOLUMENAME = "world_volume"

	# solids
	solid  = '\n    <solids>\n'
	solid += '        <box lunit="%s" name="%s" x="%s" y="%s" z="%s" />\n'%(LUNIT,SOLIDNMAE,WORLD_BOX_SIZE,WORLD_BOX_SIZE,WORLD_BOX_SIZE)
	solid += '    </solids>\n'

	# structure 
	includes  = "\n\n"
	for fname in infiles:
		gdmlname = stl_to_gdml(fname)
		includes += '            <physvol>\n'
		includes += '                <file name="%s"/>\n'%gdmlname
		includes += '             </physvol>\n'

	includes += "\n"
	structure = STRUCTURE%(VOLUMENAME,"Vacuum", SOLIDNMAE,includes)

	# world
	world = WORLD%VOLUMENAME


	# create top level gdml file
	outname = outname+".gdml"
	fout = open(outname,"w")
	fout.write(HEADER)
	fout.write(SCHEMA)
	fout.write(VACUUM)
	fout.write(solid)
	fout.write(structure)
	fout.write(world)
	fout.write(FOOTER)
	fout.close()
	
		



__is_help__()
if len(sys.argv)<3:
	__print__('Not enough argumnets provided! see  "python %s -h" for more details'%MODULE_NAME)
	raise SystemExit
matchnames = [item for item in sys.argv[2:] if sys.argv[1].lower().split('.gdml')[0] == item.lower().split('.stl')[0]]
if matchnames:
	__print__('[out_name] should not coincide with one of the input .stl file names  "python %s -h" for more details'%MODULE_NAME)
	__print__('[out_name] = ' + sys.argv[1] + ' mathces with ' + matchnames[0] + ' - please use different name for the [out_name], for example "top.gdml"')
	raise SystemExit
if ".stl" in sys.argv[1]:
	__print__('Please provide output file name! see  "python %s -h" for more details'%MODULE_NAME)
	raise SystemExit
creat_gdml_bundle(sys.argv[1].split('.gdml')[0],sys.argv[2:])
	
