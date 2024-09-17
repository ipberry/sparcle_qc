import os
import json
import sys

from pymol.cgo import *
from math import *
from pymol import cmd
import argparse
from glob import glob
import os




#this is a converter to ignore protonation states because we want to allow different protonation between the proteins but still consider this the same residue
# load Me_dictionary
def match_resi(Me_PDB_lines, Cl_PDB_lines):
    #this function will use the 'neighborhood' of a given Me residue to match it to the residue in the cl pdb 
    #inputs are the PDB lines from both
    #output will be a dictionary that has the cl residue as the key and the me residue as the value
    #'residue' is considered 3 letter code + resnum (eg LEU251) 
    me_resis = []
    cl_resis = []
    mapping_dict = {}
    #because the resnum may not be the same between the pdbs, we need a list of basically just the sequence to match the neighborhoods
    for i in range(len(Me_PDB_lines)):
        if [Me_PDB_lines[i][3][:-1], Me_PDB_lines[i][5]] not in me_resis:
            me_resis.append([Me_PDB_lines[i][3][:-1], Me_PDB_lines[i][5]])
    for i in range(len(Cl_PDB_lines)):
        if [Cl_PDB_lines[i][3][:-1], Cl_PDB_lines[i][5]] not in cl_resis:
            cl_resis.append([Cl_PDB_lines[i][3][:-1], Cl_PDB_lines[i][5]])
    for me_num, me_resi in enumerate(me_resis):
        for cl_num,cl_resi in enumerate(cl_resis):
            true_count = 0
            for i in range(0,5):
                try:
                    if cl_resis[cl_num+i][0]==me_resis[me_num+i][0]:
                        true_count +=1
                except:
                    if cl_resis[cl_num+i-5][0]==me_resis[me_num+i-5][0]:
                            true_count +=1
            if true_count==5:
                mapping_dict[cl_resi[0]+cl_resi[1]] = me_resi[0] + me_resi[1]
                break
    return mapping_dict


def check_resi_me(Me_d,Me_PDB_lines):
    #this function checks to see how much of a given residue is in the QM region
    #will return f for full residue, c for only the carbonyl or xc for everything except the carbonyl or n for none of the residue 
    QM_list = []
    for key in Me_d:
        if 'Q' in key:
            for entry in Me_d[key]:
                QM_list.append(entry)
    resi_dict = {}
    return_dict = {}
    for i in range(len(Me_PDB_lines)):
        if Me_PDB_lines[i][3][:-1]+Me_PDB_lines[i][5] not in resi_dict:
            resi_dict[Me_PDB_lines[i][3][:-1]+Me_PDB_lines[i][5]] = [Me_PDB_lines[i][1]]
        else:
            resi_dict[Me_PDB_lines[i][3][:-1]+Me_PDB_lines[i][5]].append(Me_PDB_lines[i][1])
    for resi in resi_dict:
        atom_present_counter=0
        for atom in resi_dict[resi]:
            if int(atom) in QM_list:
                atom_present_counter+=1
        if atom_present_counter == len(resi_dict[resi]):
            return_dict[resi] = 'f'
        elif atom_present_counter ==2:
            return_dict[resi] = 'c'
        elif atom_present_counter == len(resi_dict[resi])-2:
            return_dict[resi] = 'xc'
        elif atom_present_counter ==0:
            return_dict[resi] = 'n'
        else:
            print(f'ERROR: Residue {resi} in Me_PDB does not match the three cases')
            sys.exit()
    return return_dict



def convert_dictionary(cutoff,template_path):     
    with open(Me_DICT_PATH, 'r') as dictfile:
        Me_d = json.load(dictfile)
    Me_PDB_PATH = template_path 
    #path for the smalled sub
    Cl_PDB_PATH = '../cx_autocap_fixed.pdb'

    Me_DICT_PATH = glob(f'{os.path.dirname(Me_PDB_PATH)}/*/dictionary.dat')[0]
    Me_PDB_lines = []
    with open(Me_PDB_PATH, 'r') as Me_PDB_file:
        all_Me_PDB_lines = Me_PDB_file.readlines()
        for line in all_Me_PDB_lines:
            if line.startswith('ATOM') or line.startswith('HETATM'):
                Me_PDB_lines.append([line[0:6].strip(),line[6:11].strip(), line[11:16].strip(), line[16:20].strip(), line[20:22].strip(), line[22:26].strip(), line[26:38].strip(), line[38:46].strip(), line[46:54].strip(), line[54:60].strip(), line[60:66].strip(), line[66:79].strip()])
    Cl_PDB_lines = []
    with open(Cl_PDB_PATH, 'r') as Cl_PDB_file:
        all_Cl_PDB_lines = Cl_PDB_file.readlines()
        for line in all_Cl_PDB_lines:
            if line.startswith('ATOM') or line.startswith('HETATM'):
                Cl_PDB_lines.append([line[0:6].strip(),line[6:11].strip(), line[11:16].strip(), line[16:20].strip(), line[20:22].strip(), line[22:26].strip(), line[26:38].strip(), line[38:46].strip(), line[46:54].strip(), line[54:60].strip(), line[60:66].strip(), line[66:79].strip()])
    grab_dict = check_resi_me(Me_d,Me_PDB_lines)
    mapping = match_resi(Me_PDB_lines, Cl_PDB_lines)
   
    me_atom_dict = {}
    for line in Me_PDB_lines:
        me_atom_dict[line[1]]= line[3][:-1]+line[5]
    Cl_d = {'QM':[],'MM':[]}
    boundary_atoms = {}
    unique_keys = [key for key in Me_d.keys() if key!='QM' and key!='MM']
    for key in unique_keys:
        for atom in Me_d[key]:
            res = me_atom_dict[str(atom)]
            identifier = res+Me_PDB_lines[int(atom)-1][2]
            boundary_atoms[identifier] = key
    old_res = None
    with open('ligand.pdb') as lig:
        lig_lines = lig.readlines()
    lig_res = lig_lines[0][16:20].strip()
    for line in Cl_PDB_lines:
        if line[3]==lig_res:
            pass
        else:
        #look up Me resi
            if line[3][:-1]+line[5] in mapping and 'HOH' not in line[3]+line[5]:
                mapped_resi = mapping[line[3][:-1]+line[5]] 
                grab = grab_dict[mapped_resi]
                identifier = mapped_resi+line[2]
                if identifier in boundary_atoms:
                    key = boundary_atoms[identifier]
                    if key in Cl_d:
                        Cl_d[key].append(int(line[1]))
                    else:
                        Cl_d[key] = [int(line[1])]
                elif grab == 'f':
                    Cl_d['QM'].append(int(line[1]))
                elif grab == 'n':
                    Cl_d['MM'].append(int(line[1]))
                elif grab == 'c':
                    if line[2]=='C' or line[2]=='O':
                        Cl_d['QM'].append(int(line[1]))
                    else:
                        Cl_d['MM'].append(int(line[1]))
                elif grab == 'xc':
                    if line[2]=='C' or line[2]=='O':
                        Cl_d['MM'].append(int(line[1]))
                    else:
                        Cl_d['QM'].append(int(line[1]))
                else:
                    pass
            else:
                if line[3]+line[5]!=old_res:
                    old_res = line[3]+line[5]
                    cmd.reinitialize()
                    # Load PDB
                    cmd.load(Cl_PDB_PATH,"pdb")
                    cmd.show("sticks", "all")
                    cmd.label("all", "name")
                    cmd.select('close', f'organic and not solvent and not resname NME and not resname NMA and not resname ACE around {args.cutoff}')
                    cmd.select('QM',f'close and id {line[1]}')
                    inqm = cmd.count_atoms('QM')
                    #check distance
                    if inqm == 1:
                        Cl_d['QM'].append(int(line[1]))
                        QM = True
                    else:
                        Cl_d['MM'].append(int(line[1]))
                        QM = False
                else:
                    if QM:
                        Cl_d['QM'].append(int(line[1]))

                    else:
                        Cl_d['MM'].append(int(line[1]))
    with open('dictionary.dat', 'w+') as wfile:
        json.dump(Cl_d, wfile)