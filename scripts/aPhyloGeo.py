﻿import subprocess
import time  
import pandas as pd
import os
import yaml
import re
import shutil
import Bio as Bio 
from Bio import SeqIO
from Bio import pairwise2
from Bio.pairwise2 import format_alignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Align import MultipleSeqAlignment
from multiprocess import Process, Manager
from MultiProcessor import Multi
from Bio import Phylo
from Bio.Phylo.TreeConstruction import DistanceTreeConstructor
from Bio.Phylo.TreeConstruction import _DistanceMatrix
from csv import writer
from multiprocess import Process, Manager
from yaml.loader import SafeLoader


# We open the params.yaml file and put it in the params variable
with open('./scripts/params.yaml') as f:
    params = yaml.load(f, Loader=SafeLoader)
    print(params)

bootstrap_threshold = params["bootstrap_threshold"]
rf_threshold = params["rf_threshold"]
window_size = params["window_size"]
step_size = params["step_size"]
data_names = ['ALLSKY_SFC_SW_DWN_newick', 'T2M_newick', 'QV2M_newick', 
                'PRECTOTCORR_newick', 'WS10M_newick']
reference_gene_file = params["reference_gene_file"]
file_name = params["file_name"]
specimen = params["specimen"]
names = params["names"]

def openCSV(nom_fichier_csv):
    df = pd.read_csv(nom_fichier_csv)
    return df


def getDissimilaritiesMatrix(df, column_with_specimen_name, column_to_search):
    """
    Creation of a list containing the names of specimens and minimums 
    tempratures

    Args:
        df (content of CSV file)
        column_with_specimen_name (first column of names)
        column_to_search (column to compare with the first one)
    
    Return:
        The dissimilarities matrix

    """
    meteo_data = df[column_to_search].tolist()
    nom_var = df[column_with_specimen_name].tolist()
    nbr_seq = len(nom_var)
    max_value = 0
    min_value = 0

    # First loop that allow us to calculate a matrix for each sequence
    temp_tab = []

    for e in range(nbr_seq):
        # A list that will contain every distances before normalisation
        temp_list = []
        for i in range(nbr_seq):
            maximum = max(float(meteo_data[e]), float(meteo_data[i]))
            minimum = min(float(meteo_data[e]), float(meteo_data[i]))
            distance = maximum - minimum
            temp_list.append(float("{:.6f}".format(distance)))

        # Allow to find the maximum and minimum value for the weather value and 
        # then to add the temporary list in an array   
        if max_value < max(temp_list):
            max_value = max(temp_list)
        if min_value > min(temp_list):
            min_value = min(temp_list)
        temp_tab.append(temp_list)

    # Calculate normalised matrix
    tab_df = pd.DataFrame(temp_tab)
    dm_df = (tab_df - min_value)/(max_value - min_value)
    dm_df = dm_df.round(6)

    matrix = [dm_df.iloc[i,:i+1].tolist() for i in range(len(dm_df))]
    dm = _DistanceMatrix(nom_var, matrix)
    return dm


def leastSquare(tree1, tree2):
    """
    Method that calculates the least square distance between two trees.
    Trees must have the same number of leaves.
    Leaves must all have a twin in each tree.
    A tree must not have duplicate leaves
     x   x
    ╓╫╖ ╓╫╖
    123 312
 
    Args:
        tree1 (distanceTree object from biopython)
        tree2 (distanceTree object from biopython)
    
    Return:
        return result (double) the final distance between the two 
        
    """
    ls = 0.00
    leaves1 = tree1.get_terminals()
  
    leavesName = list(map(lambda l: l.name,leaves1))
 
    for i in leavesName:
        leavesName.pop(0)
        for j in leavesName:
            d1=(tree1.distance(tree1.find_any(i), tree1.find_any(j)))
            d2=(tree2.distance(tree2.find_any(i), tree2.find_any(j)))
            ls+=(abs(d1-d2))
    return ls


def draw_trees(trees):
    """
    Function that will draw the trees for each climatic variable.
    The DistanceTreeConstructor object is transformed to Newick format and 
    loaded as a toytree MulTitree object. Some stylings are applied and the 
    resulting trees are drawed into a .pdf in the viz/ dir.
    
    Args:
        trees (Dictionnary of DistanceTreeConstructor object with climatic 
        variable for keys)

    """
    trees_newick= {}
    toytrees = []
    
    for k,v in trees.items():
        trees_newick[k] = v.format('newick')
        ttree = toytree.tree(trees_newick[k], tree_format=1)
        toytrees.append(ttree)
    mtree = toytree.mtree(toytrees)

    # Setting up the stylings for nodes
    for tree in mtree.treelist:
        tree.style.edge_align_style={'stroke':'black','stroke-width':1}
        for node in tree.treenode.traverse():
            if node.is_leaf():
                node.add_feature('color', toytree.colors[7]) 
            else:
                node.add_feature('color', toytree.colors[1])  
    colors = tree.get_node_values('color', show_root=1, show_tips=1) 

    # Draw the climatic trees
    canvas, axes, mark = mtree.draw(nrows = round(len(mtree)/5), 
                                    ncols=len(mtree), height=400, width=1000,
                                    node_sizes=8, node_colors=colors, 
                                    tip_labels_align=True);

    for i in range(len(mtree)):
        rand_color = "#%03x" % random.randint(0, 0xFFF)
        axes[i].text(0,mtree.ntips,names[i+1],style={'fill':rand_color,
                    'font-size':'10px', 'font-weight':'bold'});

    toyplot.pdf.render(canvas,'../viz/climactic_trees.pdf')


def createTree(dm):
    '''
    Create a dna tree from content coming from a fasta file.

    Args:
        dm (content used to create the tree)

    Return:
        tree (the new tree)
    '''
    constructor = DistanceTreeConstructor()
    tree = constructor.nj(dm)
    return tree


def climaticPipeline(file_name, names):
    '''
    To do
    '''
    trees = {}
    df = openCSV(file_name)
    for i in range(1, len(names)):
        dm = getDissimilaritiesMatrix(df, names[0], names[i])
        trees[names[i]] = createTree(dm)

    leastSquare(trees[names[1]],trees[names[2]])


climaticPipeline(file_name, names)


def openFastaFile(reference_gene_file):
    '''
    Reads the .fasta file and read every line to get the
    sequence to analyze.

    Args:
        reference_gene_file (the fasta file to read)

    Return:
        sequences (a dictionnary containing the data from fasta file)
    '''
    sequences = {}
    with open(reference_gene_file) as sequencesFile:
        for sequence in SeqIO.parse(sequencesFile,"fasta"):
            sequences[sequence.id] = sequence.seq
    return sequences


"""
Method that aligns two DNA sequences using an algorithm.

ex.: alignSingle( "ACTTTCG" , "ACTACG" )
Could output "ACT--ACG"

Args:
    original    (String) The DNA sequence to compare to
    next        (String) The DNA sequence to modify using the original
    resultList  (List) The list containing the results.
Return:
"""
def alignSingle(args):
    #originalKey = args[0]
    original = args[1]
    nextKey = args[2]
    next = args[3]
    aligned = pairwise2.align.globalxx(str(original), str(next), one_alignment_only = True)
    return [nextKey, aligned]

"""
Method that aligns multiple DNA sequences.
The first speciment of the dataset is used as the main pivot.
This method uses parrallel computing.

Args:
    sequences (Dictionary) 
        Key is the ID of the specimen
        Data is the specimen's DNS sequence

Return:
    resultList (Dictionary) 
        Key is the ID of the specimen
        Data is the specimen's DNS sequence
"""
def alignSequences(sequences):

    firstKey = max(sequences, key=sequences.get)
    firstSeq = sequences[firstKey]
    sequences.pop(firstKey)

    list = []
    for key in sequences.keys():
        list.append([firstKey,firstSeq,key, sequences[key]])

    result = Multi(list,alignSingle).processingLargeData()

    #resultDict = {firstKey:Seq(firstSeq)}
    resultDict = {firstKey:Seq(result[0][1][0].seqA)}
    for i in result:
        resultDict[i[0]] = Seq(i[1][0].seqB)

    return resultDict

def slidingWindow2(alignedSequences):
    windowedSequences={}
    stepStart = step_size
    winSize = window_size
    stepEnd = step_size + winSize

    for key in alignedSequences.keys():
        seq = alignedSequences[key]
        winSeq = seq[stepStart : stepEnd ]
        winKey = str(key) + "_" + str(step_size) + "_" + str(stepEnd)
        windowedSequences[winKey]=Seq(winSeq)

    print (windowedSequences)
    return windowedSequences
"""
not worth the effort

def slidingWindowMulti(alignedSequences,windowSize,stepSize):
    resultList={}
    
    stepEnd = stepSize + windowSize
    multiList = []

    def winOnce(args):
        seq=args[0]
        key=args[1]
        
        winSeq = seq[stepSize : stepEnd]
        winKey = str(key) + "_" + str(stepSize) + "_" + str(stepEnd)
        return({winKey:Seq(winSeq)})

    for key in alignedSequences.keys():
        multiList.append([alignedSequences[key], key])
    resultList= Multi(multiList,winOnce).processingSmallData()
    
    resultDict={}
    for d in resultList:
        resultDict.update(d)

    print (resultDict)
    print (resultDict.keys())

    return resultDict

"""

def geneticPipeline(reference_gene_file, window_size, step_size, 
                    bootstrap_threshold, rf_threshold, data_names):
    '''
    To do
    '''
    sequences = openFastaFile(reference_gene_file)
    alignedSequences = alignSequences(sequences)
    windowedSequences = slidingWindow2(alignedSequences)
    #files = os.listdir("output/windows")
    #for file in files:
    #    os.system("cp output/windows/" + file + " infile")
    #    createBoostrap()
    #    createDistanceMatrix()
    #    createUnrootedTree()
    #    createConsensusTree() # a modifier dans la fonction
    #    filterResults(reference_gene_file, bootstrap_threshold, rf_threshold, 
    #                  data_names, number_seq, file)
    

geneticPipeline(reference_gene_file, window_size, step_size, bootstrap_threshold, 
                rf_threshold, data_names)


def prepareDirectory():
    '''
    To do
    '''
    path_output_windows = './output/windows'                            
    isExist = os.path.exists(path_output_windows)

    if isExist:
        for f in os.listdir(path_output_windows):
            os.remove(os.path.join(path_output_windows, f))
    else:
        os.makedirs(path_output_windows)

    # delete the results of last analysis
    delete_path = os.listdir('output')

    for item in delete_path:
        if item.endswith("_gene"):
            shutil.rmtree('output'+'/'+item)
        
    delete_path2 = os.listdir()
    for item in delete_path2:
        if item == "output.csv" or item.startswith("RAxML_") or item.startswith("outtree"):
            os.remove(item)
    
    with open('output.csv', 'w') as f:
        f.write("Gene,Arbre phylogeographique,Position ASM," + 
                "Bootstrap moyen,RF normalise\n")


"""
def slidingWindow(window_size=0, step=0):
    '''
    Get the total number of lines in the file.

    Args:
        window_size ()
        step ()
    '''
    try:
        f = open("infile", "r")
        line_count = -1
        for line in f:
            if line != "\n":
                line_count += 1
        f.close()
        f = open("infile", "r").read()

        num_seq = int((f.split("\n")[0]).split(" ")[0])
        longueur = int((f.split("\n")[0]).split(" ")[1])
        # we obtain the number of lines for every sequences
        no_line = int(line_count/num_seq)

        # get sequence for each variants
        with open("outfile", "w") as out:
            depart = 1
            fin = depart + no_line
            # we know the lenght for every sequences
            # we'll get every sequences and we rewrite it in an other file
            for i in range(0, int(num_seq)):
                f = open("infile", "r")
                lines_to_read = range(depart, fin)
                for position, line in enumerate(f):
                    if position in lines_to_read:
                        out.write(line)
                out.write("\n")
                depart = fin
                fin = depart + no_line
        out.close()  

        # we create a file named out that contain every sequences without
        # blank spaces and we save each name in a list in order
        with open("outfile", "r") as out, open("out", "w") as f:
            sequences = out.read().split("\n\n")
            list_names = []
            for seq in sequences:
                s = seq.replace("\n", " ").split(" ")
                if s[0] != "":
                    list_names.append(s[0])
                s_line = s[1:len(seq)]
                for line in s_line:
                    if line != "":
                        f.write(line)
                f.write("\n")
        out.close()  
        f.close()

        # slide the window along the sequence
        debut = 0
        fin = debut + window_size
        while fin <= longueur:
            index = 0 
            with open("out", "r") as f, open("output/windows/" + str(debut) + 
                                             "_" + str(fin), "w") as out:
                out.write(str(num_seq) + " " + str(window_size) + "\n")
                for line in f:
                    if line != "\n":
                        espece = list_names[index]
                        nbr_espaces = 11 - len(espece)   
                        out.write(espece)
                        for i in range(nbr_espaces):
                            out.write(" ")
                        out.write(line[debut:fin] + "\n")
                        index = index + 1
            out.close()
            f.close()
            debut = debut + step
            fin = fin + step            
    except:
        print("An error occurred.")

    # clean up
    os.system("rm out outfile infile")
"""

def createBoostrap():
    '''
    To do
    '''
    filesize = os.path.getsize("infile")
    if filesize == 0:
        raise Exception("Infile for bootstrap was empty.")
    os.system("./exec/seqboot < input/bootstrap_input.txt")
    subprocess.call(["mv", "outfile", "infile"])

def createDistanceMatrix():
    '''
    To do
    '''
    os.system("./exec/dnadist < input/dnadist_input.txt")
    subprocess.call(["mv", "outfile", "infile"])

def createUnrootedTree():
    '''
    To do
    '''
    os.system("./exec/neighbor < input/neighbor_input.txt")
    subprocess.call(["rm", "infile", "outfile"])
    subprocess.call(["mv", "outtree", "intree"])


def createConsensusTree():
    '''
    To do
    '''
    os.system("./exec/consense < input/input.txt")
    # subprocess.call(["mv", "outtree", file])
    subprocess.call(["rm", "intree", "outfile"])

def filterResults(gene, bootstrap_threshold, rf_threshold, data_names, 
                  number_seq, aligned_file):
    '''
    To do
    '''
    bootstrap_average = calculateAverageBootstrap()
    if bootstrap_average < float(bootstrap_threshold):
        subprocess.call(["rm", "outtree"])
    else:
        for tree in data_names:
            #print(tree)
            calculateRfDistance(tree)
            rfn = standardizedRfDistance(number_seq)
            if rfn == None:                 
                raise Exception(f'La distance RF n\'est pas calculable ' + 
                                'pour {aligned_file}.')                    
            if rfn <= rf_threshold:
                runRaxML(aligned_file, gene, tree)
                cleanUp(aligned_file, tree)
                bootstrap_rax = calculateAverageBootstrapRax()
                if bootstrap_rax < float(bootstrap_threshold):
                    continue
                else:
                    calculateRfDistance(tree)
                    rfn_rax = standardizedRfDistance(number_seq)
                    if rfn_rax == None:     #  '<=' not supported between instances of 'NoneType' and 'int'
                        raise Exception(f'La distance RF pour Rax n\'est pas calculable pour {aligned_file}.')         # fix it 
                    if rfn_rax <= rf_threshold:
                        addToCsv(gene, tree, aligned_file, bootstrap_rax, rfn_rax)
                        keepFiles(gene, aligned_file, tree)
                        # a verifier ici
        subprocess.call(["rm", "outtree"])

def calculateAverageBootstrap():
    '''
    To do
    '''
    total = 0
    f = open("outtree", "r").read()
    numbers = re.findall(r'[)][:]\d+[.]\d+', f)
    for number in numbers:
        total = total + float(number[2:])
    if len(numbers) >0:
        average = total / len(numbers)
    else:
        average = -1
    return average

def calculateRfDistance(tree):
    '''
    To do
    '''
    os.system("cat " + tree + " >> infile")
    os.system("cat outtree >> infile")
    os.system("./exec/rf infile outfile tmp matrix")

def standardizedRfDistance(number_seq):
    '''
    To do
    '''
    # clean up the repository
    subprocess.call(["rm", "infile", "matrix", "tmp"])
    # find the rf
    f = open("outfile", "r").read()
    words = re.split(r'[ \n]', f)
    for i in range(len(words)):
        if words[i] == "=":
            rf = int(words[i+1])
            normalized_rf = (rf/(2*number_seq-6))*100
            subprocess.call(["rm", "outfile"])
            return normalized_rf

def runRaxML(aligned_file, gene, tree):
    '''
    To do
    '''
    current_dir = os.getcwd()
    file_name = os.path.basename(aligned_file + "_" + tree)
    input_path = os.path.join(current_dir, "output", "windows", aligned_file)

    # output_path = os.path.join(current_dir, "output", gene + "_gene")
    # IL FAUT CHANGER LE MODELE SELON LE GENE CHOISI
    os.system("./exec/raxmlHPC -s " + input_path + " -n " + file_name + " -N 100 -m " +
              "GTRGAMMA -x 123 -f a -p 123")
    # output_path = os.path.join(output_path, file_name)
    # subprocess.call(["cp", input_path, output_path])

def cleanUp(file, tree):
    '''
    To do
    '''
    file = "RAxML_bipartitionsBranchLabels."+file+"_"+tree
    # directory = os.path.join("output", gene + "_gene", file)
    subprocess.call(["mv", file, "outtree"])
    files_to_delete = ['*bipartitions.*', '*bootstrap*', '*info*', '*bestTree*']
    for file in files_to_delete:
        os.system("rm -rf " +file)

def calculateAverageBootstrapRax():
    '''
    To do
    '''
    total = 0
    f = open("outtree", "r").read()
    numbers = re.findall(r'[\[]\d+[\]]', f)
    for number in numbers:
        total = total + float(number[1:(len(number)-1)])
    if len(numbers) > 0 :
        average = total / len(numbers)
    else:
        average = -1
    return average

def addToCsv(gene, tree, file, bootstrap_average, rfn):
    '''
    To do
    '''
    list = [gene, tree, file, bootstrap_average, rfn]
    with open('output.csv', 'a') as f_object:
        writer_object = writer(f_object)
        writer_object.writerow(list)
        f_object.close()

def keepFiles(gene, aligned_file, tree):
    '''
    To do
    '''
    current_dir = os.getcwd()
    file_name = os.path.basename(aligned_file + "_" + tree + "_tree")
    input_path = os.path.join(current_dir, "output", "windows", aligned_file)
    output_path = os.path.join(current_dir, "output", gene + "_gene")
    tree_path = os.path.join(output_path, file_name)
    subprocess.call(["cp", input_path, output_path]) # on garde l'ASM initial
    subprocess.call(["cp", "outtree", tree_path]) # on transfere l'arbre a garder dans le bon fichier
    subprocess.call(["mv", "output/windows/"+aligned_file+".reduced", output_path])