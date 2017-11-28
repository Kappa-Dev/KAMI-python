"""Unit testing of nugget generators functionality."""

from regraph.primitives import (print_graph)

from kami.resolvers.generators import NuggetContainer, Generator
from kami.interactions import (Modification,
                               BinaryBinding)
from kami.entities import (Gene, Region, RegionActor, Residue,
                           Site, SiteActor, State)
from kami.hierarchy import KamiHierarchy
from kami.exceptions import KamiError


class TestBlackBox(object):
    """Test class for black box functionality."""

    def __init__(self):
        """Define some initial content of the hierarchy."""
        hierarchy = KamiHierarchy()
        gene = Gene("P00533")
        gene_id = hierarchy.add_gene(gene)
        self.generator = Generator(hierarchy)
        self.default_ag_gene = gene_id

    def test_state_generator(self):
        """Test state generation."""
        state_true = State("activity", True)
        state_false = State("activity", False)

        nugget = NuggetContainer()
        nugget.ag_typing[self.default_ag_gene] = self.default_ag_gene

        # If the parameter 'add_agents' is set to false
        # this should raise an exception as there is no
        # corresponding state in the ag yet
        # try:
        old_ag_size = len(self.generator.hierarchy.action_graph.nodes())
        state1 = self.generator._generate_state(
            nugget, state_true,
            self.default_ag_gene, add_agents=False)

        state2 =\
            self.generator._generate_state(
                nugget, state_true, self.default_ag_gene)
        state3 =\
            self.generator._generate_state(
                nugget, state_false, self.default_ag_gene, add_agents=False)
        assert(
            False not in
            self.generator.hierarchy.action_graph.node[
                nugget.ag_typing[state2]]['activity'])

        state4 =\
            self.generator._generate_state(
                nugget, state_false, self.default_ag_gene, add_agents=True)

        assert(len(nugget.graph.nodes()) == 4)
        # only one node was added to the action graph
        assert(
            len(self.generator.hierarchy.action_graph.nodes()) ==
            old_ag_size + 1)

        assert("activity" in nugget.graph.node[state1].keys())
        assert("activity" in nugget.graph.node[state2].keys())
        assert("activity" in nugget.graph.node[state3].keys())
        assert("activity" in nugget.graph.node[state4].keys())

        assert(nugget.meta_typing[state1] == "state")
        assert(nugget.meta_typing[state2] == "state")
        assert(nugget.meta_typing[state3] == "state")
        assert(nugget.meta_typing[state4] == "state")

        assert(state1 not in nugget.ag_typing.keys())
        assert(state3 not in nugget.ag_typing.keys())
        assert(nugget.ag_typing[state2] == nugget.ag_typing[state4])
        assert(
            nugget.ag_typing[state2] in
            self.generator.hierarchy.action_graph.nodes())
        assert(
            nugget.ag_typing[state4] in
            self.generator.hierarchy.action_graph.nodes())
        assert(
            (nugget.ag_typing[state2], self.default_ag_gene) in
            self.generator.hierarchy.action_graph.edges())
        assert(
            (nugget.ag_typing[state4], self.default_ag_gene) in
            self.generator.hierarchy.action_graph.edges())
        return

    def test_residue_generator(self):
        """Test residue generation."""
        t = Residue("T")
        t100 = Residue("T", 100)
        y100_phospho = Residue("Y", 100, State("phosphorylation", True))
        y100_active = Residue("Y", 100, State("activity", True))

        nugget = NuggetContainer()
        nugget.ag_typing[self.default_ag_gene] = self.default_ag_gene

        old_ag_size = len(self.generator.hierarchy.action_graph.nodes())
        residue1, state1 =\
            self.generator._generate_residue(
                nugget, t, self.default_ag_gene, add_agents=False)
        assert(state1 is None)
        assert(residue1 not in nugget.ag_typing.keys())
        assert(residue1 in nugget.graph.nodes())

        residue2, _ =\
            self.generator._generate_residue(
                nugget, t, self.default_ag_gene, add_agents=True)
        assert(residue2 in nugget.ag_typing.keys())

        residue3, _ =\
            self.generator._generate_residue(
                nugget, t100, self.default_ag_gene)
        assert(nugget.ag_typing[residue2] != nugget.ag_typing[residue3])

        residue4, state4 =\
            self.generator._generate_residue(
                nugget, y100_phospho, self.default_ag_gene)
        assert(state4 is not None)
        assert(nugget.ag_typing[residue4] == nugget.ag_typing[residue3])

        residue5, state5 =\
            self.generator._generate_residue(
                nugget, y100_active, self.default_ag_gene)

        assert(len(nugget.graph.nodes()) == 7)
        assert(
            len(self.generator.hierarchy.action_graph.nodes()) ==
            old_ag_size + 4)

        assert("T" in nugget.graph.node[residue1]["aa"])
        assert("T" in nugget.graph.node[residue2]["aa"])
        assert("T" in nugget.graph.node[residue3]["aa"])
        assert(
            "T" in self.generator.hierarchy.action_graph.node[
                nugget.ag_typing[residue2]]["aa"])
        assert(100 in nugget.graph.node[residue3]["loc"])
        assert(
            100 in self.generator.hierarchy.action_graph.node[
                nugget.ag_typing[residue3]]["loc"])

        assert(nugget.meta_typing[residue1] == "residue")
        assert(nugget.meta_typing[residue2] == "residue")
        assert(nugget.meta_typing[residue3] == "residue")
        assert(nugget.meta_typing[residue4] == "residue")
        assert(nugget.meta_typing[residue5] == "residue")

        assert(
            nugget.ag_typing[residue3] ==
            nugget.ag_typing[residue4] ==
            nugget.ag_typing[residue5])

        assert(
            (nugget.ag_typing[state5], nugget.ag_typing[residue3]) in
            self.generator.hierarchy.action_graph.edges() and
            (nugget.ag_typing[state4], nugget.ag_typing[residue3]) in
            self.generator.hierarchy.action_graph.edges()
        )

    def test_site_generator(self):
        """Test site generation."""
        # Test site identification
        site_bob = Site(name="bob")
        site100_200 = Site(start="100", end="200")
        site110_150 = Site(start="110", end="150")

        site_bob_500_600 = Site(name="bob", start=500, end=600)
        site_bob_800_1000 = Site(name="bob", start=800, end=1000)
        site_bob_1 = Site(name="bob", order=1)
        site_bob_2 = Site(name="bob", order=2)

        nugget = NuggetContainer()
        nugget.ag_typing[self.default_ag_gene] = self.default_ag_gene

        old_ag_size = len(self.generator.hierarchy.action_graph.nodes())

        site_bob_id_1 =\
            self.generator._generate_site(
                nugget, site_bob, self.default_ag_gene, add_agents=False)
        assert(site_bob_id_1 in nugget.graph.nodes())
        assert(site_bob_id_1 not in nugget.ag_typing.keys())

        site_bob_id_2 =\
            self.generator._generate_site(
                nugget, site_bob, self.default_ag_gene, add_agents=True)
        assert(site_bob_id_2 in nugget.graph.nodes())
        assert(site_bob_id_2 in nugget.ag_typing.keys())

        site100_200_id =\
            self.generator._generate_site(
                nugget, site100_200, self.default_ag_gene, add_agents=True)
        site110_150_id =\
            self.generator._generate_site(
                nugget, site110_150, self.default_ag_gene, add_agents=True)
        assert(
            nugget.ag_typing[site110_150_id] ==
            nugget.ag_typing[site100_200_id])

        site_bob_500_600_id =\
            self.generator._generate_site(
                nugget, site_bob_500_600,
                self.default_ag_gene, add_agents=True)
        site_bob_800_1000_id =\
            self.generator._generate_site(
                nugget, site_bob_800_1000,
                self.default_ag_gene, add_agents=True)
        site_bob_1_id =\
            self.generator._generate_site(
                nugget, site_bob_1, self.default_ag_gene, add_agents=True)
        site_bob_2_id =\
            self.generator._generate_site(
                nugget, site_bob_2, self.default_ag_gene, add_agents=True)
        assert(
            nugget.ag_typing[site_bob_1_id] ==
            nugget.ag_typing[site_bob_500_600_id])
        assert(
            nugget.ag_typing[site_bob_2_id] ==
            nugget.ag_typing[site_bob_800_1000_id])

        assert(len(nugget.graph.nodes()) == 8)
        assert(
            len(self.generator.hierarchy.action_graph.nodes()) ==
            old_ag_size + 3)

        # Test generation of the site conditions
        complex_site = Site(
            start=500, end=600,
            states=[State('active', True)],
            residues=[Residue("Y", 1000, State('phosphorylation', True))],
        )
        try:
            self.generator._generate_site(
                nugget, complex_site, self.default_ag_gene, add_agents=True)
            raise ValueError("Invalid residue was not caught!")
        except:
            pass

        complex_site = Site(
            start=500, end=600,
            states=[State('active', True)],
            residues=[Residue("Y", 505, State('phosphorylation', True))]
        )
        complex_site_id = self.generator._generate_site(
            nugget, complex_site, self.default_ag_gene, add_agents=True
        )
        assert(
            nugget.ag_typing[complex_site_id] ==
            nugget.ag_typing[site_bob_500_600_id])
        assert(len(nugget.graph.nodes()) == 13)
        assert(len(nugget.graph.edges()) == 3)

    def test_region_generator(self):
        """Test region generation."""
        kinase_region = Region(
            name="Pkinase",
            start=300,
            end=500,
            states=[State("activity", True)],
            residues=[Residue("Y", 1000)],
            # sites=[]
        )

        nugget = NuggetContainer()
        nugget.ag_typing[self.default_ag_gene] = self.default_ag_gene

        old_ag_size = len(self.generator.hierarchy.action_graph.nodes())

        try:
            self.generator._generate_region(
                nugget, kinase_region, self.default_ag_gene, add_agents=False)
            raise ValueError("Invalid residue was not caught!")
        except KamiError:
            pass

        kinase_region = Region(
            name="Pkinase",
            start=300,
            end=500,
            states=[State("activity", True)],
            residues=[Residue("Y", 350, State("phosphorylation", True))],
            sites=[
                # Site(name="bob", residues=[Residue("Y", 350)]),
                Site(name="alice", start=1000, end=2000)
            ]
        )
        try:
            self.generator._generate_region(
                nugget, kinase_region, self.default_ag_gene, add_agents=False)
            raise ValueError("Invalid site was not caught!")
        except KamiError:
            pass
        # assert(kinase_region_id_1 in nugget.graph.nodes())
        # assert(kinase_region_id_1 not in nugget.ag_typing.keys())

        # kinase_region_id_2 =\
        #     self.generator._generate_region(
        #         nugget, kinase_region, self.default_ag_gene, add_agents=True)
        # assert(kinase_region_id_2 in nugget.graph.nodes())
        # assert(kinase_region_id_2 in nugget.ag_typing.keys())


        # assert(len(nugget.graph.nodes()) == 8)
        # assert(
        #     len(self.generator.hierarchy.action_graph.nodes()) ==
        #     old_ag_size + 3)


    # def test_gene_generator(self):
    #     """Test gene genaration."""

    #     hierarchy = KamiHierarchy()
    #     generator = Generator(hierarchy)

    #     nugget = NuggetContainer()

    #     gene = Gene(
    #         "P00519",
    #         synonyms=["ABL1"],
    #         states=[State("active", True), State("active", False)],
    #         residues=[
    #             Residue("Y", 100, State("phosphorylation", True)),
    #             Residue("S", 500),
    #             Residue("T")
    #         ],
    #         sites=[],
    #         regions=[],
    #         bounds=[],
    #     )

    #     nugget_gene_id = generator._generate_gene(
    #         nugget, gene
    #     )

    #     # check it is consistent
    #     assert(len(nugget.graph.nodes()) == 7)
    #     assert(len(nugget.graph.edges()) == 6)
    #     assert(nugget_gene_id in nugget.graph.nodes())
    #     assert("P00519" in nugget.graph.node[nugget_gene_id]['uniprotid'])
    #     assert(nugget.ag_typing["P00519_active"] == nugget.ag_typing["P00519_active_1"])

    #     print(nugget.meta_typing)
    #     print_graph(nugget.graph)
    #     print_graph(hierarchy.action_graph)

    # def test_region_actor_generator(self):
    #     pass

    # def test_site_actor_generator(self):
    #     pass

    # def test_is_bnd_generator(self):
    #     pass

    # def test_mod_generator(self):
    #     pass

    # def test_bnd_generator(self):
    #     pass