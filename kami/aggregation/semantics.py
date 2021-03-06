"""Collection of utils for semantic updates in KAMI corpuss."""
import warnings

from kami.exceptions import KamiHierarchyWarning
from kami.utils.generic import _generate_fragment_repr
from regraph.rules import Rule, NXGraph


def _propagate_semantics_to_ag(corpus, nugget_id,
                               semantic_nugget_id):
    """Propagate semantic rels from a nugget to the ag."""
    semantic_nugget_typing = corpus._hierarchy.get_typing(
        semantic_nugget_id, "semantic_action_graph")
    for nugget_node, semantics in corpus._hierarchy.get_relation(
            nugget_id, semantic_nugget_id).items():
        ag_node = corpus._hierarchy.get_typing(
            nugget_id, corpus._action_graph_id)[nugget_node]
        for s in semantics:
            corpus._hierarchy.set_node_relation(
                corpus._action_graph_id, "semantic_action_graph",
                ag_node, semantic_nugget_typing[s])


def apply_mod_semantics(corpus, nugget_id):
    """Apply mod semantics to the created nugget."""
    template_rel = corpus._hierarchy.get_relation(
        "mod_template", nugget_id)

    bnd_template_rel = None
    if "bnd_template" in corpus._hierarchy.adjacent_relations(nugget_id):
        bnd_template_rel = corpus._hierarchy.get_relation(
            "bnd_template", nugget_id)

    enzyme = None
    if "enzyme" in template_rel.keys():
        enzyme = list(template_rel["enzyme"])[0]

    if enzyme is None:
        return None

    mod_state = None
    if "mod_state" in template_rel.keys():
        mod_state = list(template_rel["mod_state"])[0]
    mod_residue = None

    if "substrate_residue" in template_rel.keys():
        mod_residue = list(template_rel["substrate_residue"])[0]

    mod_node = list(template_rel["mod"])[0]
    ag_enzyme = None
    ag_typing = corpus._hierarchy.get_typing(
        nugget_id, corpus._action_graph_id)
    if enzyme is not None:
        ag_enzyme = ag_typing[enzyme]
        enzyme_uniprot = corpus.get_uniprot(ag_enzyme)

    ag_mod_node = ag_typing[mod_node]
    ag_bnd_node = None
    bnd_node = None
    if bnd_template_rel:
        bnd_node = list(bnd_template_rel["bnd"])[0]
        ag_bnd_node = ag_typing[bnd_node]

    ag_sag_rel = corpus._hierarchy.get_relation(
        corpus._action_graph_id,
        "semantic_action_graph")

    phospho = False

    nugget = corpus.get_nugget(nugget_id)

    if enzyme is not None and mod_state is not None:
        if "phosphorylation" in nugget.get_node(
                mod_state)["name"]:
            if True in nugget.get_node(mod_node)["value"]:
                phospho = True
            # elif False in nugget.get_node(mod_node)["test"]:
            #     dephospho = True

    # 1. Phospho semantics
    if phospho:
        phospho_semantic_rel = {
            "mod": "phospho",
            mod_state: "phospho_state",
        }

        if mod_residue is not None:
            phospho_semantic_rel[mod_residue] = "phospho_target_residue"

        if bnd_node:
            phospho_semantic_rel[bnd_node] = "protein_kinase_bnd"

        if "enzyme_region" in template_rel.keys():
            # Enzyme region is specified in the nugget
            enz_region = list(template_rel["enzyme_region"])[0]
            ag_enz_region = ag_typing[enz_region]
            if ag_enz_region in ag_sag_rel.keys() and\
                    "protein_kinase" in ag_sag_rel[ag_enz_region]:
                # This enzyme region is typed by the protein kinase
                # in the action graph
                phospho_semantic_rel[enz_region] = "protein_kinase"

                # 1. MOD action merge
                kinase_mods =\
                    corpus.ag_successors_of_type(
                        ag_enz_region, "mod")

                if len(kinase_mods) > 1:
                    pattern = NXGraph()
                    pattern.add_nodes_from(
                        [ag_enz_region] + kinase_mods)

                    mod_merge_rule = Rule.from_transform(pattern)
                    new_mod_id = mod_merge_rule.inject_merge_nodes(
                        kinase_mods)

                    message = (
                        "Merged modification actions ({}) ".format(
                            kinase_mods) +
                        "of the protein kinase {} ".format(
                            _generate_fragment_repr(
                                corpus, ag_enzyme,
                                ag_enz_region)) +
                        "of the protoform with the UniProt AC '{}'".format(enzyme_uniprot)
                    )
                    rhs_ag = corpus.rewrite(
                        corpus._action_graph_id, mod_merge_rule,
                        instance={
                            n: n for n in mod_merge_rule.lhs.nodes()
                        },
                        message=message,
                        update_type="auto")
                # 1.5 BND action merge
                if bnd_template_rel:
                    kinase_bnds =\
                        corpus.ag_successors_of_type(
                            ag_enz_region, "bnd")
                    if len(kinase_bnds) > 1:
                        pattern = NXGraph()
                        pattern.add_nodes_from(
                            [ag_enz_region] + kinase_bnds)

                        bnd_merge_rule = Rule.from_transform(pattern)
                        new_mod_id = bnd_merge_rule.inject_merge_nodes(
                            kinase_bnds)
                        message = (
                            "Merged binding actions ({}) ".format(
                                kinase_bnds) +
                            "of the protein kinase {} ".format(
                                _generate_fragment_repr(
                                    corpus, ag_enzyme,
                                    ag_enz_region)) +
                            "of the protoform with the UniProt AC '{}'".format(enzyme_uniprot)
                        )
                        rhs_ag = corpus.rewrite(
                            corpus._action_graph_id, bnd_merge_rule,
                            instance={
                                n: n for n in bnd_merge_rule.lhs.nodes()
                            }, message=message, update_type="auto")

                # 2. Autocompletion
                enz_region_predecessors = nugget.predecessors(enz_region)

                # Check if kinase activity is specified in the nugget
                activity_found = False

                for pred in enz_region_predecessors:
                    ag_pred = ag_typing[pred]
                    ag_pred_type = corpus.get_action_graph_typing()[ag_pred]
                    pred_attrs = nugget.get_node(pred)
                    if ag_pred_type == "state" and\
                       "activity" in pred_attrs["name"] and\
                       True in pred_attrs["test"]:
                        phospho_semantic_rel[pred] = "protein_kinase_activity"
                        activity_found = True
                        break
                if activity_found is False:
                    # If activity is not specified, we autocomplete
                    # nugget with it
                    autocompletion_rule = Rule.from_transform(nugget)
                    new_activity_state = "{}_activity".format(enzyme)
                    autocompletion_rule.inject_add_node(
                        new_activity_state,
                        {"name": "activity", "test": True})
                    autocompletion_rule.inject_add_edge(
                        new_activity_state, enz_region)
                    # identify if there already exists the activity state
                    # in the action graph
                    rhs_typing = {corpus._action_graph_id: {}}
                    ag_activity = corpus.get_activity_state(ag_enz_region)

                    if ag_activity is not None:
                        rhs_typing[corpus._action_graph_id][new_activity_state] =\
                            ag_activity

                    # Apply autocompletion rule
                    message = (
                        "Autocompleted the nugget '{}' ".format(
                            nugget_id) +
                        "with an activity state "
                        "of the protein kinase {} ".format(
                            _generate_fragment_repr(
                                corpus, ag_enzyme,
                                ag_enz_region)) +
                        "of the protoform  with the UniProt AC '{}'".format(enzyme_uniprot)
                    )
                    rhs_g = corpus.rewrite(
                        nugget_id, autocompletion_rule,
                        rhs_typing=rhs_typing,
                        message=message,
                        update_type="auto")
                    phospho_semantic_rel[rhs_g[new_activity_state]] =\
                        "protein_kinase_activity"
            else:
                # Phosphorylation is performed by the region not
                # identified as a protein kinase
                warnings.warn(
                    "Region '{}' performing phosphorylation is not "
                    "a protein kinase region".format(ag_enz_region),
                    KamiHierarchyWarning)
        elif "enzyme_site" in template_rel:
            pass
        else:
            # Enzyme region is NOT specified in the nugget
            enz_region = None
            # Search for the unique kinase region associated
            # with respective protoform in the action graph
            unique_kinase_region =\
                corpus.unique_kinase_region(ag_enzyme)

            if unique_kinase_region is not None:
                # 1. MOD action merge
                kinase_mods =\
                    corpus.ag_successors_of_type(
                        unique_kinase_region, "mod")
                # 1.5 BND action merge
                kinase_bnds = []
                if bnd_template_rel:
                    kinase_bnds =\
                        corpus.ag_successors_of_type(
                            unique_kinase_region, "bnd")

                pattern = NXGraph()
                pattern.add_nodes_from(
                    [ag_mod_node, ag_enzyme])
                pattern.add_edges_from([(ag_enzyme, ag_mod_node)])

                if ag_bnd_node:
                    pattern.add_nodes_from([ag_bnd_node])
                    pattern.add_edges_from([(ag_enzyme, ag_bnd_node)])

                mod_merge_rule = Rule.from_transform(pattern)
                mod_merge_rule.inject_remove_edge(ag_enzyme, ag_mod_node)
                if ag_bnd_node:
                    mod_merge_rule.inject_remove_edge(ag_enzyme, ag_bnd_node)

                merged_actions_str = []
                merged_mods = None
                if len(kinase_mods) > 0:
                    # generate a rule that merges mods
                    for n in kinase_mods:
                        mod_merge_rule._add_node_lhs(n)
                    merged_mods = [ag_mod_node] + kinase_mods
                    new_mod_id = mod_merge_rule.inject_merge_nodes(merged_mods)
                    merged_actions_str.append(
                        "merged MOD-mechanisms {}".format(merged_mods)
                        if merged_mods else "")

                merged_bnds = None
                if len(kinase_bnds) > 0:
                    for n in kinase_bnds:
                        mod_merge_rule._add_node_lhs(n)
                    merged_bnds = [ag_bnd_node] + kinase_bnds
                    new_bnd_id = mod_merge_rule.inject_merge_nodes(merged_bnds)
                    merged_actions_str.append(
                        "merged BND-mechanisms {}".format(merged_bnds)
                        if merged_bnds else "")

                message = (
                    "Rewired phosphorylation ('{}') to be mediated by ".format(
                        ag_mod_node) +
                    "the existing protein kinase {} ".format(
                        _generate_fragment_repr(
                            corpus, ag_enzyme, unique_kinase_region)) +
                    "of the protoform with the UniProt AC '{}' {}".format(
                        enzyme_uniprot,
                        "({})".format(", ".join(merged_actions_str))
                        if len(merged_actions_str) > 0
                        else "")
                )
                rhs_ag = corpus.rewrite(
                    corpus._action_graph_id, mod_merge_rule,
                    instance={
                        n: n for n in mod_merge_rule.lhs.nodes()
                    }, message=message, update_type="auto")

                # 2. Autocompletion
                if len(kinase_mods) > 0:
                    new_ag_mod = rhs_ag[new_mod_id]
                else:
                    new_ag_mod = ag_mod_node

                if len(kinase_bnds) > 0:
                    new_ag_bnd = rhs_ag[new_bnd_id]
                else:
                    new_ag_bnd = ag_bnd_node

                autocompletion_rule = Rule.from_transform(nugget)
                autocompletion_rule.inject_add_node(
                    unique_kinase_region,
                    corpus.action_graph.get_node(unique_kinase_region))

                activity_state = "{}_activity".format(unique_kinase_region)

                autocompletion_rule.inject_add_node(
                    activity_state, {"name": "activity", "test": True})
                autocompletion_rule.inject_add_edge(
                    unique_kinase_region, enzyme)
                autocompletion_rule.inject_add_edge(
                    unique_kinase_region, mod_node)
                autocompletion_rule.inject_add_edge(
                    activity_state, unique_kinase_region)

                rhs_typing = {
                    corpus._action_graph_id: {
                        unique_kinase_region: unique_kinase_region,
                        mod_node: new_ag_mod,
                    }
                }

                if ag_bnd_node:
                    rhs_typing[corpus._action_graph_id][bnd_node] = new_ag_bnd

                ag_activity = corpus.get_activity_state(
                    unique_kinase_region)
                if ag_activity is not None:
                    rhs_typing[corpus._action_graph_id][activity_state] = ag_activity

                message = (
                    "Autocompleted the nugget '{}' ".format(
                        nugget_id) +
                    "with the protein kinase {} ".format(
                        _generate_fragment_repr(
                            corpus, ag_enzyme,
                            unique_kinase_region)) +
                    "of the protoform with the UniProt AC '{}'".format(enzyme_uniprot)
                )

                rhs_nugget = corpus.rewrite(
                    nugget_id, autocompletion_rule,
                    instance={
                        n: n for n in autocompletion_rule.lhs.nodes()
                    },
                    rhs_typing=rhs_typing,
                    message=message, update_type="auto")

                enz_region = rhs_nugget[unique_kinase_region]
                phospho_semantic_rel[rhs_nugget[unique_kinase_region]] =\
                    "protein_kinase"
                for k, v in corpus._hierarchy.get_typing(
                        nugget_id, corpus._action_graph_id).items():
                    if v == ag_activity:
                        nugget_activity = k
                phospho_semantic_rel[rhs_nugget[activity_state]] =\
                    "protein_kinase_activity"
                corpus._hierarchy.set_node_relation(
                    nugget_id, "mod_template", enz_region, "enzyme_region")
            else:
                # The repective protoform in the action graph contains
                # either no or multiple kinase regions
                warnings.warn(
                    "Could not find the unique protein kinase "
                    "region associated with the protoform '%s'" % ag_enzyme,
                    KamiHierarchyWarning)

        # Add a relation to the phosporylation semantic nugget
        corpus.add_semantic_nugget_rel(
            nugget_id,
            "phosphorylation_semantic_nugget",
            phospho_semantic_rel)
        # propagate this phospho semantics to the ag nodes
        _propagate_semantics_to_ag(
            corpus, nugget_id, "phosphorylation_semantic_nugget")


def apply_bnd_semantics(corpus, nugget_id):
    """Apply known binding semantics to the created nugget."""

    nugget = corpus.get_nugget(nugget_id)

    def _apply_sh2_py_semantics(region_node, region_bnd, partner_gene,
                                partner_region=None, partner_site=None):
        ag_typing = corpus._hierarchy.get_typing(
            nugget_id, corpus._action_graph_id)

        ag_region = ag_typing[region_node]
        ag_protoform = corpus.get_protoform_of(ag_region)
        protoform_uniprot = corpus.get_uniprot(ag_protoform)
        ag_sag_relation = corpus._hierarchy.get_relation(
            corpus._action_graph_id,
            "semantic_action_graph")

        if ag_region in ag_sag_relation.keys() and\
           "sh2_domain" in ag_sag_relation[ag_region]:
            sh2_semantic_rel = {
                region_node: "sh2_domain",
                region_bnd: "sh2_domain_pY_bnd",
            }

            # Check if there are multiple bnd actions associated with the
            # same SH2 domain, merge them if it's the case
            ag_region_bnds = []
            for bnd in corpus.ag_successors_of_type(ag_region, "bnd"):
                ag_region_bnds.append(bnd)
            if len(ag_region_bnds) > 1:
                # generate a rule that merges bnds and loci
                pattern = NXGraph()
                pattern.add_nodes_from(ag_region_bnds)
                bnd_merge_rule = Rule.from_transform(pattern)
                bnd_merge_rule.inject_merge_nodes(ag_region_bnds)
                message = (
                    "Merged binding actions ({}) ".format(
                        ag_region_bnds) +
                    "of the SH2 {} ".format(
                        _generate_fragment_repr(
                            corpus, ag_protoform, ag_region)) +
                    "of the protoform with the UniProt AC '{}'".format(protoform_uniprot)
                )
                corpus.rewrite(
                    corpus._action_graph_id, bnd_merge_rule,
                    message=message, update_type="auto")

            # Process/autocomplete pY sites and Y residues
            if partner_site:
                ag_partner_site = ag_typing[partner_site]
                ag_partner_protoform = corpus.get_protoform_of(ag_partner_site)
                partner_uniprot = corpus.get_uniprot(ag_partner_protoform)

                sh2_semantic_rel[partner_site] = "pY_site"
                # check if site has phosphorylated 'Y' residue
                py_residue_states = []
                for pred in nugget.predecessors(
                        partner_site):
                    ag_pred = ag_typing[pred]
                    if corpus.get_action_graph_typing()[ag_pred] == "residue" and\
                       "Y" in nugget.get_node(pred)["aa"]:
                        for residue_pred in nugget.predecessors(pred):
                            ag_residue_pred = ag_typing[residue_pred]
                            if corpus.get_action_graph_typing()[
                                    ag_residue_pred] == "state" and\
                               "phosphorylation" in nugget.get_node(residue_pred)["name"]:
                                py_residue_states.append((pred, residue_pred))
                # if pY residue was not found it, autocomplete nugget with it
                if len(py_residue_states) == 0:
                    pattern = NXGraph()
                    pattern.add_nodes_from([partner_site])
                    autocompletion_rule = Rule.from_transform(pattern)
                    autocompletion_rule.inject_add_node(
                        "pY_residue", {"aa": "Y"})
                    autocompletion_rule.inject_add_node(
                        "pY_residue_phospho",
                        {"name": "phosphorylation", "test": True})
                    autocompletion_rule.inject_add_edge(
                        "pY_residue_phospho", "pY_residue")
                    autocompletion_rule.inject_add_edge(
                        "pY_residue", partner_site)
                    rhs_typing = {
                        "meta_model": {
                            "pY_residue": "residue",
                            "pY_residue_phospho": "state"
                        }
                    }
                    message = (
                        "Autocompleted the nugget '{}' ".format(
                            nugget_id) +
                        "by additing a phosphorylated Y to {}".format(
                            _generate_fragment_repr(
                                corpus,
                                ag_partner_protoform, ag_partner_site, "site")) + 
                        "of the protoform with the UniProt AC '{}'".format(
                            partner_uniprot)
                    )
                    rhs_nugget = corpus.rewrite(
                        nugget_id, autocompletion_rule, instance={
                            n: n for n in autocompletion_rule.lhs.nodes()
                        },
                        rhs_typing=rhs_typing,
                        message=message, update_type="auto")

                    # add necessary semantic rels
                    sh2_semantic_rel[rhs_nugget["pY_residue"]] = "pY_residue"
                    sh2_semantic_rel[rhs_nugget["pY_residue_phospho"]] =\
                        "phosphorylation"
                else:
                    # Add semantic rels
                    for residue, state in py_residue_states:
                        sh2_semantic_rel[residue] = "pY_residue"
                        sh2_semantic_rel[state] = "phosphorylation"

                    # Update action graph by merging all the sites
                    # sharing the same residue
                    residues = corpus.get_attached_residues(ag_partner_site)
                    if len(residues) == 1:
                        ag_gene = ag_typing[partner_gene]
                        sites_to_merge = set()
                        sites = [
                            s for s in corpus.get_attached_sites(ag_gene)
                            if s != ag_partner_site]
                        for s in sites:
                            s_residues = corpus.get_attached_residues(s)
                            if len(s_residues) == 1:
                                if residues[0] == s_residues[0]:
                                    sites_to_merge.add(s)
                        if len(sites_to_merge) > 0:
                            message = (
                                "Merged sites ('{}')".format(sites_to_merge) +
                                "with the pY {} ".format(
                                    _generate_fragment_repr(
                                        corpus,
                                        ag_partner_protoform, ag_partner_site, "site")) + 
                                "of the protoform with the UniProt AC '{}' (sites share residues)".format(
                                    partner_uniprot)
                            )
                            sites_to_merge.add(ag_partner_site)
                            pattern = NXGraph()
                            pattern.add_nodes_from(sites_to_merge)
                            site_merging_rule = Rule.from_transform(pattern)
                            site_merging_rule.inject_merge_nodes(sites_to_merge)
                            corpus.rewrite(
                                corpus._action_graph_id, site_merging_rule,
                                message=message, update_type="auto")
            else:
                # Generate a rule that adds pY site with a phospho Y residue
                if partner_region is not None:
                    attached_to = partner_region
                else:
                    attached_to = partner_gene
                pattern = NXGraph()
                pattern.add_nodes_from([region_bnd, attached_to])
                pattern.add_edges_from([(attached_to, region_bnd)])
                autocompletion_rule = Rule.from_transform(pattern)
                autocompletion_rule.inject_remove_edge(
                    attached_to, region_bnd)
                autocompletion_rule.inject_add_node("pY_site")
                autocompletion_rule.inject_add_node(
                    "pY_residue", {"aa": "Y"})
                autocompletion_rule.inject_add_node(
                    "pY_residue_phospho",
                    {"name": "phosphorylation", "test": True})
                autocompletion_rule.inject_add_edge(
                    "pY_residue_phospho", "pY_residue")
                autocompletion_rule.inject_add_edge(
                    "pY_residue", "pY_site")
                autocompletion_rule.inject_add_edge(
                    "pY_site", attached_to)
                autocompletion_rule.inject_add_edge(
                    "pY_site", region_bnd)
                rhs_typing = {
                    "meta_model": {
                        "pY_site": "site",
                        "pY_residue": "residue",
                        "pY_residue_phospho": "state"
                    }
                }

                message = (
                    "Autocompleted the nugget '{}' ".format(
                        nugget_id) +
                    "by additing a pY site " +
                    "to the protoform with the UniProt AC '{}'".format(
                        corpus.get_uniprot(ag_typing[partner_gene]))
                )

                # Rewrite nugget and propagate to the AG
                rhs_nugget = corpus.rewrite(
                    nugget_id, autocompletion_rule,
                    rhs_typing=rhs_typing,
                    message=message, update_type="auto")

                partner_site = rhs_nugget["pY_site"]

                sh2_semantic_rel[partner_site] = "pY_site"
                sh2_semantic_rel[rhs_nugget["pY_residue"]] = "pY_residue"
                sh2_semantic_rel[rhs_nugget["pY_residue_phospho"]] =\
                    "phosphorylation"

            return sh2_semantic_rel
        return None

    template_rel = corpus._hierarchy.get_relation(
        "bnd_template", nugget_id)

    if "left_partner_region" in template_rel.keys():

        region_node =\
            list(template_rel["left_partner_region"])[0]
        region_bnd =\
            list(template_rel["bnd"])[0]

        partner_site = None
        if "right_partner_site" in template_rel.keys():
            partner_site = list(template_rel["right_partner_site"])[0]
        partner_region = None
        if "right_partner_region" in template_rel.keys():
            partner_region = list(template_rel["right_partner_region"])[0]
        partner_gene = list(template_rel["right_partner"])[0]

        sh2_semantic_rel = _apply_sh2_py_semantics(
            region_node, region_bnd, partner_gene, partner_region,
            partner_site)
        if sh2_semantic_rel is not None:
            corpus.add_semantic_nugget_rel(
                nugget_id,
                "sh2_pY_binding_semantic_nugget",
                sh2_semantic_rel)
            _propagate_semantics_to_ag(
                corpus, nugget_id, "sh2_pY_binding_semantic_nugget")

    if "right_partner_region" in template_rel.keys():
        region_node =\
            list(template_rel["right_partner_region"])[0]
        region_bnd =\
            list(template_rel["bnd"])[0]

        partner_site = None
        if "left_partner_site" in template_rel.keys():
            partner_site = list(template_rel["left_partner_site"])[0]
        partner_region = None
        if "left_partner_region" in template_rel.keys():
            partner_region = list(template_rel["left_partner_region"])[0]
        partner_gene = list(template_rel["left_partner"])[0]

        sh2_semantic_rel = _apply_sh2_py_semantics(
            region_node, region_bnd, partner_gene, partner_region,
            partner_site)

        if sh2_semantic_rel is not None:
            corpus.add_semantic_nugget_rel(
                nugget_id,
                "sh2_pY_binding_semantic_nugget",
                sh2_semantic_rel)
            _propagate_semantics_to_ag(
                corpus, nugget_id, "sh2_pY_binding_semantic_nugget")
