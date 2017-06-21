"""
Set of utils for agent anatomy.

Provide the structural features of a protein based on information from
biological knowledge databases.
"""
import copy
import json
import os
import re
import requests
import warnings

from xml.dom import minidom

import xml.etree.ElementTree as etree

ENSEMBL_SERVER = 'http://rest.ensembl.org'
INTERPROFILE = 'interpro.xml'

IPR_MATCHES = '/home/slegare/ENS/InterPro/interpro_swiss_match-63.xml'
IPR_SIGNATURES = '/home/slegare/ENS/InterPro/interpro_shortnames-63.xml'

# Read InterPro matched (IPR_MATCHES) and 
# InterPro signatures (IPR_SIGNATURES) and keep them in memory.
print('Loading SwissProt-InterPro matches ....... ')
ipr_matches = open(IPR_MATCHES, 'r').read()
ipr_matches_root = etree.fromstring(ipr_matches)
print('Done')
ipr_signatures = open(IPR_SIGNATURES, 'r').read()
ipr_signatures_root = etree.fromstring(ipr_signatures)


class AnatomizerError(Exception):
    """Base class for anatomizer exception."""


class AnatomizerWarning(UserWarning):
    """Base class fro anatomizer warning."""


def _fetch_ensembl(ext):
    r = requests.get(ENSEMBL_SERVER + ext,
                     headers={"Content-Type": "application/json"})
    if not r.ok:
        r.raise_for_status()
        raise AnatomizerError(
            "Error fetching Ensembl data by url '%s'" %
            ext
        )
    return r.json()


def get_ensembl_gene(query, species=None, workdir=None):
    """."""
    if not workdir:
        workdir = "anatomyfiles"
    if not species:
        species = "homo_sapiens"

    os.makedirs(workdir, exist_ok=True)

    ensemblext = '/xrefs/symbol/%s/%s?' % (species, query)
    decoded = _fetch_ensembl(ensemblext)
    genes = []

    for entry in decoded:
        ensid = entry['id']
        if ensid[0:4] == 'ENSG':
            genes.append(ensid)
    if len(genes) == 1:
        ensemblgene = genes[0]
        return ensemblgene
    elif len(genes) == 0:
        raise AnatomizerError(
            "Could not find Ensembl Gene ID for query '%s'" %
            query
        )
    else:
        print(genes)
        raise AnatomizerError(
            "Could not find unique Ensembl Gene ID for query '%s'" %
            query
        )


def get_hgncsymbol(ensemblgene):
    """."""
    ensemblext = '/xrefs/id/%s?' % ensemblgene
    xreflist = _fetch_ensembl(ensemblext)
    hgncsymbol = None
    for xref in xreflist:
        if xref['db_display_name'] == 'HGNC Symbol':
            hgncsymbol = xref['display_id']
    return hgncsymbol


def get_strand(ensemblgene):
    """."""
    ensemblext = '/lookup/id/%s?' % ensemblgene
    lookgene = _fetch_ensembl(ensemblext)
    strand = lookgene['strand']
    return strand


def get_transcripts(ensemblgene, strand):
    """."""
    ensemblext = '/overlap/id/%s?feature=cds' % ensemblgene
    cdslist = _fetch_ensembl(ensemblext)
    defset = set()
    for cds in cdslist:
        if cds['strand'] == strand:
            # why do you need OrderedDict not just dict?
            defset.add((cds['Parent'], cds['protein_id']))
    # Remove duplicates (set does not work with dictionaries)
    protein_list = [
        {
            "Ensembl_transcr": parent,
            "Ensembl_protein": protein_id
        } for (parent, protein_id) in defset
    ]
    return protein_list


def get_hgnctranscr(enst):
    """Get HGNC transc by Ensembl transc id."""
    ensemblext = '/xrefs/id/%s?' % enst
    transcrxreflist = _fetch_ensembl(ensemblext)
    hgnctranscr = None
    for txref in transcrxreflist:
        if txref['dbname'] == 'HGNC_trans_name':
            hgnctranscr = txref['primary_id']
    return hgnctranscr


def get_unique_uniprotid(ensp):
    """Get UniProtId by Ensembl protein id."""
    ensemblext = '/xrefs/id/%s?' % ensp
    protxreflist = _fetch_ensembl(ensemblext)

    uniprot = None
    for pxref in protxreflist:
        if pxref['db_display_name'][:9] == 'UniProtKB':
            if uniprot is None:
                uniprot = pxref['primary_id']
                # # Optionally show if from Swiss-prot or TrEMBL
                # uniprot = pxref['db_display_name'][i10:]
            # else:
            #     raise ClientError(
            #         "More than one UniProt Accession Number found for '%s'" %
            #         ensp
            #     )
    return uniprot


def get_uniprotid(ensp):
    """Get UniProtId by Ensembl protein id."""
    ensemblext = '/xrefs/id/%s?' % ensp
    protxreflist = _fetch_ensembl(ensemblext)

    nunip = 0
    uniprot_ids = []
    for pxref in protxreflist:
        if pxref['db_display_name'][:9] == 'UniProtKB':
            uniprot_ids.append(pxref['primary_id'])
            # # Optionally show if from Swiss-prot or TrEMBL
            # uniprot = pxref['db_display_name'][i10:]
            nunip += 1
    if nunip > 1:
        warnings.warn(
            "More than one UniProt Accession Number found for '%s'" %
            ensp, AnatomizerWarning
        )
    return uniprot_ids


def _fetch_uniprotxml(uniprotac, workdir=None):
    """Retrieve UniProt entry from the web in xml format."""
    if not workdir:
        workdir = "anatomyfiles"

    if ('uniprot%s.xml' % uniprotac) in os.listdir(workdir):
        xmlfile = open('%s/uniprot%s.xml'
                       % (workdir, uniprotac), 'r')
        uniprot = xmlfile.read()
        print('Using UniProt entry from file %s/uniprot%s.xml.\n'
              % (workdir, uniprotac))
    else:
        r = requests.get('http://www.uniprot.org/uniprot/%s.xml'
                         % uniprotac)
        xmlparse = minidom.parseString(r.text)
        uniprot = xmlparse.toprettyxml(indent="   ", newl='')
        # Write xml to file to avoid download on future uses
        savefile = open('%s/uniprot%s.xml'
                        % (workdir, uniprotac), 'w')
        savefile.write(uniprot)
        print('Fetched file from http://www.uniprot.org/uniprot/%s.xml.\n'
              % uniprotac)
    # Removing default namespace to simplify parsing.
    xmlnonamespace = re.sub(r'\sxmlns="[^"]+"', '', uniprot, count=1)
    root = etree.fromstring(xmlnonamespace)
    return root


def get_length(ensp):
    """."""
    ensemblext = '/lookup/id/%s?' % ensp
    lookptn = _fetch_ensembl(ensemblext)
    length = None
    if 'length' in lookptn.keys():
        length = lookptn['length']
    return length


def get_canon(ensemblgene, species="homo_sapiens"):
    """ Get canonical (primary) transcript from APPRIS """
    r = requests.get('http://apprisws.bioinfo.cnio.es:80/rest/exporter/'
                     'id/%s/%s?methods=appris&format=json'
                     % (species, ensemblgene))
    try:
        appris = r.json()
    except:
        raise AnatomizerError("Some trouble finding canonical transcript!")

    canontrancripts = []
    for isoform in appris:
        try:
            an = isoform['annotation']
            rel = isoform['reliability']
            if 'Principal Iso' or 'Possible Principal Isoform' in an:
                if 'PRINCIPAL' in rel:
                    canontrancripts.append(isoform['transcript_id'])
        except:
            pass
    canonset = set(canontrancripts)
    canontrancript = None
    if len(canonset) == 1:
        canontrancript = canontrancripts[0]
    else:
        warnings.warn(
            'Cannot find unique canonical (primary) transcript',
            AnatomizerWarning
        )
    return canontrancript


def _get_uniprotdupl(protein_list):
    """."""
    seen = []
    duplicates = set()
    for ptn in protein_list:
        ac = ptn['Uniprot_id']
        if ac in seen:
            duplicates.add(ac)
        else:
            seen.append(ac)
    # Check UniProt to distinguish ENSPs that have a same UniProt AC.
    for unip in list(duplicates):
        uniprotxml = _fetch_uniprotxml(unip)
        # Check all the ENSTs from ptnlist that have AC "unip".
        for ptn in protein_list:
            if ptn["Uniprot_id"] == unip:
                enst = ptn["Ensembl_transcr"]
                try:
                    molecule = uniprotxml.find(".//dbReference[@id='%s']/"
                                               "molecule" % enst)
                    ptn['Uniprot_id'] = molecule.get('id')
                except:
                    pass


def get_features(ensemblegene):
    """Get features by ensemblgene."""
    ensemblext = '/overlap/translation/%s?' % ensemblegene
    tmplist = _fetch_ensembl(ensemblext)
    # Gene3D
    ignorelist = ['PIRSF', 'PANTHER', 'SignalP', 'Seg', 'Tmhmm', 'PRINTS']
    featurelist = []
    for feature in tmplist:
        # if feature['type'] not in ignorelist:
        #     feature_dict = {}
        #     feature_dict['description'] = feature['description']
        #     feature_dict['start'] = feature['start']
        #     feature_dict['end'] = feature['end']
        #     feature_dict['xrefs'] = {
        #         feature['type']: feature['id']
        #     }
        #     if 'interpro' in feature.keys():
        #         feature_dict['xrefs'].update({
        #             'interpro': feature['interpro']
        #         })
        #     # add here smth that tries to find a name
        #     feature_dict['name'] = None
        #     featurelist.append(feature_dict)

        # Temporarily take domains only from Pfam
        if feature['type'] == 'Pfam':
            feature_dict = {}
            feature_dict['description'] = feature['description']
            feature_dict['start'] = feature['start']
            feature_dict['end'] = feature['end']
            feature_dict['xrefs'] = {
                feature['type']: feature['id']
            }
            if 'interpro' in feature.keys():
                feature_dict['xrefs'].update({
                    'interpro': feature['interpro']
                })
            # add here smth that tries to find a name
            feature_dict['name'] = None
            featurelist.append(feature_dict)

    return featurelist

def get_ipr_features(uniprot_ac):
    """ Get features by UniProt Accession (Optionally specifying isoform). """
    ignorelist = ['PANTHER', 'SignalP', 'Seg', 'Tmhmm', 'PRINTS']
    featurelist = []
    entry = ipr_matches_root.find("protein[@id='%s']" % uniprot_ac)
    matchlist = entry.findall('match')
    for feature in matchlist:
        if feature.get('dbname') not in ignorelist:
            # Check if domain is intergrated in InterPro. Ignore otherwise.
            ipr = feature.find('ipr')
            try:
                interpro_id = ipr.get('id')
                integrated = True
            except:
                integrated = False

            # If domain has InterPro ID, add as feature.
            if integrated:

                feature_dict = {}
                feature_dict['xname'] = feature.get('name')
                feature_dict['xid'] = feature.get('id')
                feature_dict['xdatabase'] = feature.get('dbname')

                feature_dict['ipr_id'] = interpro_id
                try:
                    ipr_parent = ipr.get('parent_id')
                except:
                    ipr_parent = None
                feature_dict['ipr_parents'] = parent_chain(interpro_id, ipr_parent)

                feature_dict['ipr_name'] = ipr.get('name')

                # Get short name from file interpro.xml.
                short_name = find_shortname(feature_dict['ipr_id'])
                feature_dict['short_name'] = short_name
                feature_dict['feature_type'] = ipr.get('type')

                lcn = feature.find('lcn')
                start = int(lcn.get('start'))
                end = int(lcn.get('end'))
                length = end - start
                feature_dict['start'] = start
                feature_dict['end'] = end
                feature_dict['length'] = length

                featurelist.append(feature_dict)

    return featurelist


def find_shortname(ipr):
    """ Find the short name associated with an InterPro ID. """
    ipr_entry = ipr_signatures_root.find("interpro[@id='%s']" % ipr)
    shortname = ipr_entry.get('short_name')

    return shortname


def parent_chain(ipr, parent):
    """ 
    Build the chain of parents (as a list) from given InterPro ID
    to top of hierarchy.
    """
    parchain = []
    while parent != None:
        if parent != 'None':
            parchain.append(parent)
        # Find the entry of that parent
        ipr_entry = ipr_signatures_root.find("interpro[@id='%s']" % parent)
        # Redefine parent as the parent of the previous parent.
        try:
            parent = ipr_entry.get('parent')
        except:
            parent = None

    return parchain


def are_parents(frag1, frag2):
    """ 
    Returns True if InterPro IDs of given fragments are identical or parents.
    Returns False otherwise.
    """
    ipr1 = frag1.ipr_id
    ipr2 = frag2.ipr_id
    par1 = frag1.ipr_parents
    par2 = frag2.ipr_parents

    answer = False
    if ipr1 == ipr2:
        answer = True
    if ipr1 in par2:
        answer = True
    if ipr2 in par1:
        answer = True
   
    return answer


def _merge_overlap(f1, f2):
    """Calculate overlap ratio.

    Simple overlap ratio: number of overlapping residues /
                          total span of the two features

                -----------               -----------
    overlap     |||||||||        span  ||||||||||||||
             ------------              ------------
    """
    starts = [f1.start, f2.start]
    ends = [f1.end, f2.end]
    ratio = 0
    # First, check if there is an overlap at all.
    highstart = max(starts)
    lowend = min(ends)
    if highstart < lowend:
        # Compute number of overlapping residues
        overlap = lowend - highstart
        # Compute the total span
        lowstart = min(starts)
        highend = max(ends)
        span = highend - lowstart
        # Compute ratio
        ratio = float(overlap) / float(span)
    return ratio


def _nest_overlap(f1, f2):
    """Calculate overlap ratio for nesting.

    Nest overlap ratio: number of overlapping residues /
                          span of the smallest feature

                   --------                  --------
    overlap        ||||||        span        ||||||||
             ------------              ------------
    """
    ratio = 0
    # f1 is expected to be the largest feature
    if f1.length > f2.length:
        starts = [f1.start, f2.start]
        ends = [f1.end, f2.end]
        # First, check if there is an overlap at all.
        highstart = max(starts)
        lowend = min(ends)
        if highstart < lowend:
            # Compute number of overlapping residues.
            overlap = lowend - highstart
            # Find smallest feature span.
            span = f2.length
            # Compute ratio.
            ratio = float(overlap) / float(span)
    return ratio


class Fragment:
    """Class implementing raw domain fragment."""

    def __init__(self, internal_id, xname, xid, xdatabase, 
                 start, end, length, short_name, ipr_name,
                 ipr_id, feature_type, ipr_parents):
        """Initilize raw fragment."""
        self.internal_id = internal_id
        self.xname = xname
        self.xid = xid
        self.xdatabase = xdatabase
        self.start = start
        self.end = end
        self.length = length
        self.short_name = short_name
        self.ipr_name = ipr_name
        self.ipr_id = ipr_id
        self.feature_type = feature_type
        self.ipr_parents = ipr_parents
        return

    def to_dict(self):
        fragment_dict = {}
        fragment_dict["internal_id"] = self.internal_id
        fragment_dict["xname"] = self.xname
        fragment_dict["xid"] = self.xid
        fragment_dict["xdatabase"] = self.xdatabase
        fragment_dict["start"] = self.start
        fragment_dict["end"] = self.end
        fragment_dict["length"] = self.length
        fragment_dict["short_name"] = self.short_name
        fragment_dict["ipr_name"] = self.ipr_name
        fragment_dict["ipr_id"] = self.ipr_id
        fragment_dict["feature_type"] = self.feature_type
        fragment_dict["ipr_parents"] = self.ipr_parents

        return fragment_dict

    def print_summary(self, level=0):
        prefix = ""
        for i in range(level):
            prefix += "\t"

        if len(self.xname) > 45:
            fragname = self.xname[0:45] + "..."
        else:
            fragname = self.xname

        print(
            prefix,
            "  Fragment %2i: %s" % (self.internal_id,fragname)
        )
        print(
            prefix,
            "    Start-End: %i-%i" % (self.start, self.end)
        ) 
        print(
            prefix,
            "   References: %s: %s" % (self.xdatabase, self.xid)
        )

        return


class DomainAnatomy:
    """Class implements anatomy of a domain."""

    def __init__(self, short_names, ipr_names, ipr_ids, start, end,
                 length, feature_type, subdomains=None, fragments=None):
        self.short_names = short_names
        self.ipr_names = ipr_names
        self.ipr_ids = ipr_ids
        self.start = start
        self.end = end
        self.length = length
        self.feature_type = feature_type

        if subdomains:
            self.subdomains = subdomains
        else:
            self.subdomains = list()
        if fragments:
            self.fragments = fragments
        else:
            self.fragments = list()
        #if names:
        #    self.names = names
        #else:
        #    self.names = list()
        #self.description = desc
        return

    @classmethod
    def from_fragment(cls, fragment):
        domain = cls(
            fragment.start,
            fragment.end,
            subdomains=None,
            fragments=[copy.deepcopy(fragment)],
            names=[fragment.name],
            desc=fragment.description
        )
        return domain

    def is_protein_kinase(self):
        """Dummy is_kinase function.

        If name or description of domain mentions
        one of the key words, return True.
        """
        key_words = ["protein kinase"]
        stop_words = ["phorbol ester"]
        for key_word in key_words:
            for name in self.names:
                if name and key_word in name.lower():
                    # check for stop words
                    for stop_word in stop_words:
                        if stop_word in name.lower():
                            return False
                    # no stop words were found
                    return True
            if self.description and key_word in self.description.lower():
                # check for stop words
                for stop_word in stop_words:
                    if stop_word in name.lower():
                        return False
                # no stop words were found
                return True
        return False

    def to_dict(self):
        anatomy = dict()
        anatomy["start"] = self.start
        anatomy["end"] = self.end
        anatomy["names"] = self.names
        anatomy["desc"] = self.description

        anatomy["subdomains"] = []
        for sd in self.subdomains:
            anatomy["subdomains"].append(sd.to_dict())

        anatomy["fragments"] = []
        for fr in self.fragments:
            anatomy["fragments"].append(fr.to_dict())

        return anatomy

    def to_json(self):
        anatomy = self.to_dict()
        return json.dumps(anatomy, indent=4)

    def print_summary(self, fragments=True, level=0):
        if self.feature_type == 'Domain' or self.feature_type == 'Repeat':
            prefix = ""
            for i in range(level):
                prefix += "\t"

            if len(self.short_names) == 0:
                shorts = "None"
            else:
                shorts = ", ".join(self.short_names)
            if len(self.ipr_names) == 0:
                names = "None"
            else:
                names = ", ".join(self.ipr_names)
            if len(self.ipr_ids) == 0:
                ids = "None"
            else:
                ids = ", ".join(self.ipr_ids)

            print(prefix, "         ---> %s <---" % self.feature_type) 
            print(prefix, "     Short Names: %s" % shorts)
            print(prefix, "  InterPro Names: %s" % names)
            print(prefix, "    InterPro IDs: %s" % ids)
            print(prefix, "           Start: %s" % self.start)
            print(prefix, "             End: %s" % self.end)
            if fragments:
                if len(self.fragments) > 0:
                    print(prefix, "Source fragments: ")
                    for fragment in self.fragments:
                        fragment.print_summary(level + 3)
                        print()
            if len(self.subdomains) > 0:
                sorted_subdomains = sorted(self.subdomains, key=lambda x: x.start)
                print(prefix, "      Subdomains:")
                for domain in sorted_subdomains:
                    domain.print_summary(fragments, level=level + 2)
            return


class ProteinAnatomy:
    """Class implements protein anatomy."""

    def __init__(self, ensembl_transcr, ensembl_prot, transcr_name, uniprot_ids, primary=False):
        self.ensembl_transcr = ensembl_transcr
        self.ensembl_prot = ensembl_prot
        self.transcr_name = transcr_name
        self.uniprot_ids = uniprot_ids
        self.primary = primary

    def to_dict(self):
        anatomy = dict()

        anatomy["ensembl_transcr"] = self.ensembl_transcr
        anatomy["ensembl_prot"] = self.ensembl_prot
        anatomy["transcr_name"] = self.transcr_name
        anatomy["uniprot_ids"] = self.uniprot_ids
        anatomy["primary"] = self.primary

        return anatomy

    def to_json(self):
        anatomy = self.to_dict()
        return json.dumps(anatomy, indent=4)

    def print_summary(self):
        print("      Transcript name: %s" % self.transcr_name)
        print("Ensembl Transcript ID: %s" % self.ensembl_transcr)
        print("   Ensembl Protein ID: %s" % self.ensembl_prot)
        print("   Uniprot Accessions: %s" % ", ".join(self.uniprot_ids))


class GeneAnatomy:
    """Implements gene anatomy."""

    def _merge_fragments(self, fragments, overlap_threshold=0.7, shortest=True):
        nfeatures = len(fragments)
        ipr_overlap_threshold=0.1

        visited = set()
        groups = []

        for i in range(nfeatures):
            feature1 = fragments[i]
            if i not in visited:
                group = [feature1]
                visited.add(i)
                for j in range(i + 1, nfeatures):
                    if j not in visited:
                        feature2 = fragments[j]
                        for member in group:                                
                            overlap = _merge_overlap(member, feature2)
                            condition = are_parents(member, feature2)
                            if condition == True and overlap >= ipr_overlap_threshold:
                                group.append(feature2)
                                visited.add(j)
                                break
                groups.append(group)
        domains = []
        # create domains from groups
        for group in groups:
            # 1. find shortest non-empty description for a group
            domain_desc = None
            descs = dict([
                (
                    len(member.short_name),
                    member.short_name
                ) for member in group if member.short_name
            ])
            if len(descs) > 0:
                min_desc = min(descs.keys())
                domain_desc = descs[min_desc]

            # 2. find start/end depending on the value of parameter `shortest`
            lengths = dict([
                (member.length, i) for i, member in enumerate(group)
            ])
            # 2.a. create domain from the shortest fragment
            if shortest:
                min_length = min(lengths.keys())
                domain_start = group[lengths[min_length]].start
                domain_end = group[lengths[min_length]].end
            # 2.b. create domain from the longest fragment
            else:
                max_length = max(lengths.keys())
                domain_start = group[lengths[max_length]].start
                domain_end = group[lengths[max_length]].end
            domain_length = domain_start - domain_end

            # 3. find domain names from concatenation of all fragment names
            short_name_list = [member.short_name for member in group if member.short_name]
            ipr_name_list = [member.ipr_name for member in group if member.ipr_name]
            ipr_id_list = [member.ipr_id for member in group if member.ipr_id]
            short_names = sorted(set(short_name_list), key=lambda x: short_name_list.index(x))
            ipr_names = sorted(set(ipr_name_list), key=lambda x: ipr_name_list.index(x))
            ipr_ids = sorted(set(ipr_id_list), key=lambda x: ipr_id_list.index(x))

            # 5. get feature type
            feature_type = group[0].feature_type

            # 4. create domain object
            domain = DomainAnatomy(
                short_names,
                ipr_names,
                ipr_ids,
                domain_start,
                domain_end,
                domain_length,
                feature_type,
                subdomains=[],
                fragments=group
            )

            domains.append(domain)
        return domains

    def _nest_domains(self, nest_threshold=0.7, max_level=1):

        def _find_nests(elements, domains):
            visited = set()
            result_nest = dict()
            for i in elements:
                if i not in visited:
                    result_nest[i] = dict()
                    visited.add(i)
                    for j in elements:
                        if j not in visited:
                            overlap = _nest_overlap(
                                domains[i],
                                domains[j]
                            )
                            if overlap >= nest_threshold:
                                result_nest[i][j] = dict()
                                visited.add(j)
            return result_nest

        # Recursive auxiliary function to nest domains
        def _nest(domains, current_level):
            if current_level == max_level:
                return domains
            else:
                # sort_domains by size
                sorted_domains = sorted(domains, key=lambda x: x.length, reverse=True)

                nestsing_indices = _find_nests(
                    list(range(len(sorted_domains))), sorted_domains
                )
                result_domains = []
                for domain_index, indices in nestsing_indices.items():
                    next_level_domains = [sorted_domains[i] for i in indices]
                    nested_domains = _nest(next_level_domains, current_level + 1)
                    for domain in nested_domains:
                        sorted_domains[domain_index].subdomains.append(
                            domain
                        )
                    result_domains.append(sorted_domains[domain_index])
                return result_domains

        # 1. nest domains
        result_domains = _nest(self.domains, 0)

        return result_domains

    def __init__(self, query, features=True, merge_features=True,
                 nest_features=True, merge_overlap=0.7, nest_overlap=0.7,
                 nest_level=1):
        # 1. Get basic information about an agent
        ensemblgene = get_ensembl_gene(query)

        self.ensembl_gene = ensemblgene
        self.hgnc_symbol = get_hgncsymbol(ensemblgene)
        self.strand = get_strand(ensemblgene)

        transcripts = get_transcripts(ensemblgene, self.strand)

        canonical_transcr = get_canon(ensemblgene)
        if canonical_transcr:
            for transcr in transcripts:
                if transcr["Ensembl_transcr"] == canonical_transcr:
                    self.canonical = transcr["Ensembl_protein"]
        else:
            # For the moment, just take the first ENST as canonical.
            self.canonical = transcripts[0]["Ensembl_protein"]

        self.proteins = []
        for transcr in transcripts:
            transcript_name = get_hgnctranscr(transcr['Ensembl_transcr'])
            uniprot_ids = get_uniprotid(transcr["Ensembl_protein"])

            primary = False
            if transcr['Ensembl_protein'] == self.canonical:
                primary = True

            protein_anatomy = ProteinAnatomy(
                transcr['Ensembl_transcr'],
                transcr["Ensembl_protein"],
                transcript_name,
                uniprot_ids,
                primary
            )

            self.proteins.append(protein_anatomy)

#         _get_uniprotdupl(self.proteins)

        self.length = get_length(self.canonical)

        self.domains = []

        # 2. (optional) Get features
        fragments = []
        if features:
            #feature_list = get_features(self.canonical)
            feature_list = get_ipr_features('P51587')
            # construct fragments from features found
            fragnum = 0
            for feature in feature_list:
                fragnum += 1
                fragment = Fragment(
                    fragnum,
                    feature["xname"],
                    feature["xid"],
                    feature["xdatabase"],
                    feature["start"],
                    feature["end"],
                    feature["length"],
                    feature["short_name"],
                    feature["ipr_name"],
                    feature["ipr_id"],
                    feature["feature_type"],
                    feature["ipr_parents"]
                )
                fragments.append(fragment)
        else:
            return

        # 3. (optional) Merge features
        if merge_features:
            if not features:
                raise AnatomizerError(
                    "Cannot merge features: parameter 'features' was set to False, "
                    "no features were collected.'"
                )
            domains = self._merge_fragments(fragments, overlap_threshold=merge_overlap)
            self.domains = domains
        else:
            for fr in fragments:
                self.domains.append(
                    DomainAnatomy.from_fragment(fr)
                )
            return

        # 4. (optional) Nest features
        if nest_features:
            if not features:
                raise AnatomizerError(
                    "Cannot nest features: parameter 'features' was set to False, "
                    "no features were collected.'"
                )
            if not merge_features:
                raise AnatomizerError(
                    "Cannot nest features: parameter 'merge_features' was set to False, "
                    "features should be merged to be nested.'"
                )
            self.domains = self._nest_domains(merge_overlap, max_level=nest_level)

        return

    def to_dict(self):
        anatomy = dict()

        anatomy["ensembl_gene_id"] = self.ensembl_gene
        anatomy["hgnc_symbol"] = self.hgnc_symbol
        anatomy["strand"] = self.strand

        anatomy["proteins"] = []
        for protein in self.proteins:
            anatomy["proteins"].append(protein.to_dict())

        anatomy["length"] = self.length
        anatomy["canonical"] = self.canonical

        anatomy["domains"] = []
        for domain in self.domains:
            anatomy["domains"].append(domain.to_dict())

        return anatomy

    def to_json(self):
        anatomy = self.to_dict()
        return json.dumps(anatomy, indent=4)

    def anatomy_summary(self, fragments=True):
        """Print summary in standard order."""
        print("SUMMARY OF AGENT ANATOMY")
        print("========================")
        print()
        print("    HGNC Symbol: %s" % self.hgnc_symbol)
        print("Ensembl Gene ID: %s" % self.ensembl_gene)
        print("         Strand: %s" % self.strand)
        print("         Length: %s" % self.length)
        print()
        print("======= Proteins =======")
        print()
        print("->  Primary transcript: ")
        print()
        for protein in self.proteins:
            if protein.ensembl_prot == self.canonical:
                protein.print_summary()
        print()
        print("->  Other transctipts: ")
        print()
        sorted_proteins = sorted(self.proteins, key=lambda x: x.transcr_name)
        for protein in sorted_proteins:
            if protein.ensembl_prot != self.canonical:
                protein.print_summary()
                print()
        print("======= Domains =======")
        print()
        sorted_domains = sorted(self.domains, key=lambda x: x.start)
        for domain in sorted_domains:
            domain.print_summary(fragments)
            print()