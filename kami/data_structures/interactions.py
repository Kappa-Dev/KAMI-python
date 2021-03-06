"""Collection of classes implementing interactions."""
import sys
from .entities import (Protoform, SiteActor, RegionActor,
                       Residue, State, Region, Site, actor_from_json, actor_to_json)

from kami.exceptions import KamiError


def capitalize(s):
    ls = list(s)
    ls[0] = ls[0].upper()
    return "".join(ls)


def _target_to_json(target):
    json_data = {}
    if isinstance(target, Residue):
        json_data["type"] = "Residue"
    elif isinstance(target, State):
        json_data["type"] = "State"
    json_data["data"] = target.to_json()
    return json_data


def _target_from_json(json_data):
    if json_data["type"] == "Residue":
        return Residue.from_json(json_data["data"])
    elif json_data["type"] == "State":
        return State.from_json(json_data["data"])
    else:
        raise KamiError(
            "Cannot load modification target: invalid target type '{}'".format(
                json_data["type"]))


class Interaction(object):
    """Base class for Kami interaction."""

    def to_attrs(self):
        """Convert interaction to attribute dictionary."""
        attrs = dict()
        if self.rate is not None:
            attrs["rate"] = {str(self.rate)}
        if self.annotation is not None:
            attrs["text"] = {self.annotation}
        return attrs

    @classmethod
    def from_json(cls, json_data):
        """Create Interaction object from json."""
        return getattr(sys.modules[__name__], json_data["type"]).from_json(json_data)


class Modification(Interaction):
    """Class for Kami mod interaction."""

    def __init__(self, enzyme, substrate, target,
                 value=True, rate=None, annotation=None,
                 desc=None):
        """Initialize modification."""
        self.enzyme = enzyme
        self.substrate = substrate
        self.target = target
        self.value = value
        self.rate = rate
        self.annotation = annotation
        if desc is None:
            desc = capitalize(self.generate_desc())
        self.desc = desc

    def __str__(self):
        """String representation of Modification class."""
        if self.desc is not None:
            desc_str = self.desc
        else:
            desc_str = ""
        res = "Modification: {}\n".format(desc_str)
        res += "\tEnzyme: {}\n".format(self.enzyme)
        res += "\tSubstrate: {}\n".format(self.substrate)
        res += "\tMod target: {}\n".format(self.target)
        res += "\tValue: {}\n".format(self.value)
        if self.rate is not None:
            res += "\tRate: {}\n".format(self.rate)
        if self.annotation is not None:
            res += "\tAnnotation: {}\n".format(self.annotation)
        return res

    def __repr__(self):
        """Representation of a Modification object."""
        enzyme_rep = self.enzyme.__repr__()
        substrate_rep = self.substrate.__repr__()
        mod_target = self.target.__repr__()

        res = "Modification(" +\
            "enzyme={}, substrate={}, target={}, value={}".format(
                enzyme_rep, substrate_rep, mod_target, self.value)
        if self.rate is not None:
            res += ", rate={}".format(self.rate)
        if self.annotation is not None:
            res += ", annotation={}".format(str(self.annotation))
        if self.desc is not None:
            res += ", desc='{}'".format(self.desc)
        res += ")"
        return res

    def enzyme_site(self):
        """Test if the enzyme actor is a SiteActor."""
        return isinstance(self.enzyme, SiteActor)

    def enzyme_region(self):
        """Test if the enzyme actor is a RegionActor."""
        return isinstance(self.enzyme, RegionActor)

    def enzyme_gene(self):
        """Test if the enzyme actor is a Protoform."""
        return isinstance(self.enzyme, Protoform)

    @classmethod
    def from_json(cls, json_data):
        """Create Modification object from json representation."""
        # load enzyme
        enzyme = actor_from_json(json_data["enzyme"])
        substrate = actor_from_json(json_data["substrate"])
        target = _target_from_json(json_data["target"])

        value = True
        if "value" in json_data.keys():
            value = json_data["value"]
        rate = None
        if "rate" in json_data.keys():
            rate = json_data["rate"]
        annotation = None
        if "annotation" in json_data.keys():
            annotation = json_data["annotation"]
        desc = None
        if "desc" in json_data.keys():
            desc = json_data["desc"]
        return cls(enzyme, substrate, target, value, rate, annotation, desc)

    def to_json(self):
        json_data = {}
        json_data["type"] = "Modification"
        json_data["enzyme"] = actor_to_json(self.enzyme)
        json_data["substrate"] = actor_to_json(self.substrate)
        json_data["target"] = _target_to_json(self.target)
        json_data["value"] = self.value
        if self.rate:
            json_data["rate"] = self.rate
        if self.annotation:
            json_data["annotation"] = self.annotation
        if self.desc:
            json_data["desc"] = self.desc
        return json_data

    def generate_desc(self):
        """Generate text description of the interaction."""
        residue_rep = ""
        if isinstance(self.target, State):
            state_rep = self.target.generate_desc()
        else:
            state_rep = self.target.state.generate_desc()
            residue_rep = self.target.generate_desc()

        desc = "{} modifies the {} of the {}{}".format(
            self.enzyme.generate_desc(), state_rep, self.substrate.generate_desc(),
            " at {}".format(residue_rep) if len(residue_rep) > 0 else "")
        return desc


class Binding(Interaction):
    """Class for Kami binary binding interaction."""

    def __init__(self, left, right,
                 rate=None, annotation=None, desc=None):
        """Initialize binary binding."""
        self.left = left
        self.right = right
        self.rate = rate
        self.annotation = annotation
        if desc is None:
            desc = capitalize(self.generate_desc())
        self.desc = desc

    def __str__(self):
        """String representation of Binding class."""
        if self.desc is not None:
            desc_str = self.desc
        else:
            desc_str = ""
        res = "Binding: {}\n".format(desc_str)
        res += "\t{} binds {}\n".format(str(self.left), str(self.right))
        if self.rate is not None:
            res += "\tRate: {}\n".format(self.rate)
        if self.annotation is not None:
            res += "\tAnnotation: {}\n".format(self.annotation)
        return res

    def __repr__(self):
        """Representation of a Binding object."""
        res = "Binding(left={}, right={}".format(
            self.left.__repr__(), self.right.__repr__())
        if self.rate is not None:
            res += ", rate={}".format(self.rate)
        if self.annotation is not None:
            res += ", annotation={}".format(self.annotation)
        if self.desc is not None:
            res += ", desc='{}'".format(self.desc)
        res += ")"
        return res

    def to_json(self):
        json_data = {}
        json_data["type"] = "Binding"
        json_data["left"] = actor_to_json(self.left)
        json_data["right"] = actor_to_json(self.right)
        if self.rate:
            json_data["rate"] = self.rate
        if self.annotation:
            json_data["annotation"] = self.annotation
        if self.desc:
            json_data["desc"] = self.desc
        return json_data

    @classmethod
    def from_json(cls, json_data):
        """Create Binding object from json representation."""
        left = actor_from_json(json_data["left"])
        right = actor_from_json(json_data["right"])

        rate = None
        if "rate" in json_data.keys():
            rate = json_data["rate"]
        annotation = None
        if "annotation" in json_data.keys():
            annotation = json_data["annotation"]
        desc = None
        if "desc" in json_data.keys():
            desc = json_data["desc"]

        return cls(left, right, rate, annotation, desc)

    def generate_desc(self):
        """Generate text description of the interaction."""
        desc = "{} binds {}".format(
            self.left.generate_desc(), self.right.generate_desc())
        return desc


class Unbinding(Interaction):
    """Class for Kami unbinding interaction."""

    def __init__(self, left, right,
                 rate=None, annotation=None, desc=None):
        """Initialize unbinding."""
        self.left = left
        self.right = right
        self.rate = rate
        self.annotation = annotation
        if desc is None:
            desc = capitalize(self.generate_desc())
        self.desc = desc

    def __str__(self):
        """String representation of Unbinding class."""
        if self.desc is not None:
            desc_str = self.desc
        else:
            desc_str = ""
        res = "Unbinding: {}\n".format(desc_str)
        res += "\t{} unbinds {}\n".format(
            str(self.left), str(self.right))
        if self.rate is not None:
            res += "\tRate: {}\n".format(self.rate)
        if self.annotation is not None:
            res += "\tAnnotation: {}\n".format(self.annotation)
        return res

    def __repr__(self):
        """Representation of a Unbinding object."""
        res = "Unbinding(left={}, right={}".format(
            self.left.__repr__(), self.right.__repr__())
        if self.rate is not None:
            res += ", rate={}".format(self.rate)
        if self.annotation is not None:
            res += ", annotation={}".format(self.annotation)
        if self.desc is not None:
            res += ", desc='{}'".format(self.desc)
        res += ")"
        return res

    def to_json(self):
        json_data = {}
        json_data["type"] = "Unbinding"
        json_data["left"] = actor_to_json(self.left)
        json_data["right"] = actor_to_json(self.right)
        if self.rate:
            json_data["rate"] = self.rate
        if self.annotation:
            json_data["annotation"] = self.annotation
        if self.desc:
            json_data["desc"] = self.desc
        return json_data

    @classmethod
    def from_json(cls, json_data):
        """Create Unbinding object from json representation."""
        left = actor_from_json(json_data["left"])
        right = actor_from_json(json_data["right"])

        rate = None
        if "rate" in json_data.keys():
            rate = json_data["rate"]
        annotation = None
        if "annotation" in json_data.keys():
            annotation = json_data["annotation"]
        desc = None
        if "desc" in json_data.keys():
            desc = json_data["desc"]

        return cls(left, right, rate, annotation, desc)

    def generate_desc(self):
        """Generate text description of the interaction."""
        desc = "{} unbinds {}".format(
            self.left.generate_desc(), self.right.generate_desc())
        return desc


class SelfModification(Interaction):
    """Class for Kami SelfModification interaction."""

    def __init__(self, enzyme, target, value=True,
                 substrate_region=None, substrate_site=None, rate=None,
                 annotation=None, desc=None):
        """Initialize modification."""
        self.enzyme = enzyme
        self.substrate_region = substrate_region
        self.substrate_site = substrate_site
        self.target = target
        self.value = value
        self.rate = rate
        self.annotation = annotation
        if desc is None:
            desc = capitalize(self.generate_desc())
        self.desc = desc

    def __str__(self):
        """String representation of an SelfModification object."""
        if self.desc is not None:
            desc_str = self.desc
        else:
            desc_str = ""
        res = "SelfModification: {}\n".format(desc_str)
        res += "\tEnzyme: {}\n".format(self.enzyme)
        if self.substrate_region is not None:
            res += "Substrate region: {}\n".format(self.substrate_region)
        if self.substrate_site is not None:
            res += "Substrate site: {}\n".format(self.substrate_site)
        res += "\tMod target: {}\n".format(self.target)
        res += "\tValue: {}\n".format(self.value)
        if self.rate is not None:
            res += "\tRate: {}\n".format(self.rate)
        if self.annotation is not None:
            res += "\tAnnotation: {}\n".format(self.annotation)
        return res

    def __repr__(self):
        """Representation of an SelfModification object."""
        enzyme_rep = self.enzyme.__repr__()
        mod_target = self.target.__repr__()

        res = "SelfModification(enzyme={}, target={}, value={}".format(
            enzyme_rep, mod_target, self.value)
        if self.substrate_region is not None:
            res += ", substrate_region={}".format(
                self.substrate_region.__repr__())
        if self.substrate_site is not None:
            res += ", substrate_site={}".format(
                self.substrate_site.__repr__())
        if self.rate is not None:
            res += ", rate={}".format(self.rate)
        if self.annotation is not None:
            res += ", annotation={}".format(str(self.annotation))
        if self.desc is not None:
            res += ", desc='{}'".format(self.desc)
        res += ")"
        return res

    def to_json(self):
        json_data = {}
        json_data["type"] = "SelfModification"
        json_data["enzyme"] = actor_to_json(self.enzyme)
        json_data["target"] = _target_to_json(self.target)
        json_data["value"] = self.value
        if self.substrate_region:
            json_data["substrate_region"] = self.substrate_region.to_json()
        if self.substrate_site:
            json_data["substrate_site"] = self.substrate_site.to_json()
        if self.rate:
            json_data["rate"] = self.rate
        if self.annotation:
            json_data["annotation"] = self.annotation
        if self.desc:
            json_data["desc"] = self.desc
        return json_data

    @classmethod
    def from_json(cls, json_data):
        """Create SelfModification object from json representation."""
        # load enzyme
        enzyme = actor_from_json(json_data["enzyme"])
        target = _target_from_json(json_data["target"])

        substrate_region = None
        if "substrate_region" in json_data.keys():
            if json_data["substrate_region"] is not None:
                substrate_region = Region.from_json(json_data["substrate_region"])
        substrate_site = None
        if "substrate_site" in json_data.keys():
            if json_data["substrate_site"] is not None:
                substrate_site = Site.from_json(json_data["substrate_site"])

        value = True
        if "value" in json_data.keys():
            value = json_data["value"]
        rate = None
        if "rate" in json_data.keys():
            rate = json_data["rate"]
        annotation = None
        if "annotation" in json_data.keys():
            annotation = json_data["annotation"]
        desc = None
        if "desc" in json_data.keys():
            desc = json_data["desc"]
        return cls(
            enzyme, target=target, value=value,
            substrate_region=substrate_region, substrate_site=substrate_site,
            rate=rate, annotation=annotation, desc=desc)

    def generate_desc(self):
        """Generate text description of the interaction."""
        residue_rep = ""
        if isinstance(self.target, State):
            state_rep = self.target.generate_desc()
        else:
            state_rep = self.target.state.generate_desc()
            residue_rep = self.target.generate_desc()

        substrate_region_rep = ""
        if self.substrate_region:
            substrate_region = " of the {}".format(
                self.substrate_region.generate_desc())

        substrate_site_rep = ""
        if self.substrate_site:
            substrate_site_rep = " on {}".format(
                self.substrate_region.generate_desc())

        desc = "{} modifies its state {}{}{}{}".format(
            self.enzyme.generate_desc(), state_rep,
            " at {}".format(residue_rep) if len(residue_rep) > 0 else "",
            substrate_region_rep,
            substrate_site_rep)
        return desc


class AnonymousModification(Interaction):
    """Class for Kami anonymous modification interaction."""

    def __init__(self, substrate, target, value=True,
                 rate=None, annotation=None, desc=None):
        """Initialize modification."""
        self.enzyme = None
        self.substrate = substrate
        self.target = target
        self.value = value
        self.rate = rate
        self.annotation = annotation
        if desc is None:
            desc = capitalize(self.generate_desc())
        self.desc = desc

    def __str__(self):
        """String representation of an AnonymousModification object."""
        if self.desc is not None:
            desc_str = self.desc
        else:
            desc_str = ""
        res = "AnonymousModification: {}\n".format(desc_str)
        res += "\tSubstrate: %s\n" % self.substrate
        res += "\tMod target: %s\n" % self.target
        res += "\tValue: %s\n" % self.value
        if self.rate is not None:
            res += "\tRate: {}\n".format(self.rate)
        if self.annotation is not None:
            res += "\tAnnotation: {}\n".format(self.annotation)
        return res

    def __repr__(self):
        """Representation of an AnonymousModification object."""
        substrate_rep = self.substrate.__repr__()
        mod_target = self.target.__repr__()

        res = "AnonymousModification(" +\
            "enzyme=None, substrate={}, target={}, value={}".format(
                substrate_rep, mod_target, self.value)
        if self.rate is not None:
            res += ", rate={}".format(self.rate)
        if self.annotation is not None:
            res += ", annotation={}".format(self.annotation)
        if self.desc is not None:
            res += ", desc='{}'".format(self.desc)
        res += ")"
        return res

    def to_json(self):
        json_data = {}
        json_data["type"] = "AnonymousModification"
        json_data["substrate"] = actor_to_json(self.substrate)
        json_data["target"] = _target_to_json(self.target)
        json_data["value"] = self.value
        if self.rate:
            json_data["rate"] = self.rate
        if self.annotation:
            json_data["annotation"] = self.annotation
        if self.desc:
            json_data["desc"] = self.desc
        return json_data

    @classmethod
    def from_json(cls, json_data):
        """Create AnonymousModification object from json representation."""
        substrate = actor_from_json(json_data["substrate"])
        target = _target_from_json(json_data["target"])

        value = True
        if "value" in json_data.keys():
            value = json_data["value"]
        rate = None
        if "rate" in json_data.keys():
            rate = json_data["rate"]
        annotation = None
        if "annotation" in json_data.keys():
            annotation = json_data["annotation"]
        desc = None
        if "desc" in json_data.keys():
            desc = json_data["desc"]
        return cls(substrate, target, value, rate, annotation, desc)

    def generate_desc(self):
        """Generate text description of the interaction."""
        residue_rep = ""
        if isinstance(self.target, State):
            state_rep = self.target.generate_desc()
        else:
            state_rep = self.target.state.generate_desc()
            residue_rep = self.target.generate_desc()

        desc = "Anonymous modification of the {} of the {}{}".format(
            state_rep, self.substrate.generate_desc(),
            " at {}".format(residue_rep) if len(residue_rep) > 0 else "")
        return desc


class LigandModification(Interaction):
    """Class for Kami transmodification interaction."""

    def __init__(self, enzyme, substrate, target, value=True,
                 enzyme_bnd_subactor="protoform", substrate_bnd_subactor="protoform",
                 enzyme_bnd_region=None, enzyme_bnd_site=None,
                 substrate_bnd_region=None, substrate_bnd_site=None,
                 rate=None, annotation=None, desc=None):
        """Initialize modification."""
        self.enzyme = enzyme
        self.substrate = substrate
        self.target = target
        self.value = value
        self.enzyme_bnd_subactor = enzyme_bnd_subactor
        self.substrate_bnd_subactor = substrate_bnd_subactor
        self.enzyme_bnd_region = enzyme_bnd_region
        self.enzyme_bnd_site = enzyme_bnd_site
        self.substrate_bnd_region = substrate_bnd_region
        self.substrate_bnd_site = substrate_bnd_site
        self.rate = rate
        self.annotation = annotation
        if desc is None:
            desc = capitalize(self.generate_desc())
        self.desc = desc
        return

    def __str__(self):
        """String representation of LigandModification class."""
        if self.desc is not None:
            desc_str = self.desc
        else:
            desc_str = ""
        res = "LigandModification: {}\n".format(desc_str)
        res += "\tEnzyme: {}\n".format(self.enzyme)
        res += "\tSubstrate: {}\n".format(self.substrate)
        res += "\tMod target: {}\n".format(self.target)
        res += "\tValue: {}\n".format(self.value)
        res += "\tEnzyme binds through: {}\n".format(self.enzyme_bnd_subactor)
        res += "\tSubstrate binds through: {}\n".format(self.substrate_bnd_subactor)
        if self.enzyme_bnd_region is not None:
            res += "\tEnzyme binding region: {}\n".format(
                self.enzyme_bnd_region)
        if self.enzyme_bnd_site is not None:
            res += "\tEnzyme bindind site: {}\n".format(
                self.enzyme_bnd_site)
        if self.substrate_bnd_region is not None:
            res += "\tSubstrate binding region: {}\n".format(
                self.substrate_bnd_region)
        if self.substrate_bnd_site is not None:
            res += "\tSubstrate binding site: {}\n".format(
                self.substrate_bnd_site)
        if self.rate is not None:
            res += "\tRate: {}\n".format(self.rate)
        if self.annotation is not None:
            res += "\tAnnotation: {}\n".format(self.annotation)
        return res

    def __repr__(self):
        """Representation of a LigandModification object."""
        enzyme_rep = self.enzyme.__repr__()
        substrate_rep = self.substrate.__repr__()
        mod_target = self.target.__repr__()

        res = "LigandModification(" +\
            "enzyme={}, substrate={}, target={}, value={}".format(
                enzyme_rep, substrate_rep, mod_target, self.value)

        res += ", enzyme_bnd_subactor='{}'".format(self.enzyme_bnd_subactor)
        res += ", substrate_bnd_subactor='{}'".format(
            self.substrate_bnd_subactor)

        if self.enzyme_bnd_region is not None:
            res += ", enzyme_bnd_region={}".format(
                self.enzyme_bnd_region.__repr__())
        if self.enzyme_bnd_site is not None:
            res += ", enzyme_bnd_site={}".format(
                self.enzyme_bnd_site.__repr__())
        if self.substrate_bnd_region is not None:
            res += ", substrate_bnd_region={}".format(
                self.substrate_bnd_region.__repr__())
        if self.substrate_bnd_site is not None:
            res += ", substrate_bnd_site={}".format(
                self.substrate_bnd_site.__repr__())
        if self.rate is not None:
            res += ", rate={}".format(self.rate)
        if self.annotation is not None:
            res += ", annotation={}".format(str(self.annotation))
        if self.desc is not None:
            res += ", desc='{}'".format(self.desc)
        res += ")"
        return res

    def to_json(self):
        json_data = {}
        json_data["type"] = "LigandModification"
        json_data["enzyme"] = actor_to_json(self.enzyme)
        json_data["substrate"] = actor_to_json(self.substrate)
        json_data["target"] = _target_to_json(self.target)
        json_data["value"] = self.value
        json_data["enzyme_bnd_subactor"] = self.enzyme_bnd_subactor
        json_data["substrate_bnd_subactor"] = self.substrate_bnd_subactor
        if self.enzyme_bnd_region:
            json_data["enzyme_bnd_region"] = self.enzyme_bnd_region.to_json()
        if self.enzyme_bnd_site:
            json_data["enzyme_bnd_site"] = self.enzyme_bnd_site.to_json()
        if self.substrate_bnd_region:
            json_data["substrate_bnd_region"] = self.substrate_bnd_region.to_json()
        if self.substrate_bnd_site:
            json_data["substrate_bnd_site"] = self.substrate_bnd_site.to_json()
        if self.rate:
            json_data["rate"] = self.rate
        if self.annotation:
            json_data["annotation"] = self.annotation
        if self.desc:
            json_data["desc"] = self.desc
        return json_data

    @classmethod
    def from_json(cls, json_data):
        """Create LigandModification object from json representation."""
        enzyme = actor_from_json(json_data["enzyme"])
        substrate = actor_from_json(json_data["substrate"])
        target = _target_from_json(json_data["target"])

        value = True
        if "value" in json_data.keys():
            value = json_data["value"]

        enzyme_bnd_subactor = "protoform"
        if "enzyme_bnd_subactor" in json_data.keys():
            enzyme_bnd_subactor = json_data["enzyme_bnd_subactor"]

        substrate_bnd_subactor = "protoform"
        if "substrate_bnd_subactor" in json_data.keys():
            substrate_bnd_subactor = json_data["substrate_bnd_subactor"]

        enzyme_bnd_region = None
        if "enzyme_bnd_region" in json_data.keys() and\
           json_data["enzyme_bnd_region"] is not None:
            enzyme_bnd_region = Region.from_json(
                json_data["enzyme_bnd_region"])

        enzyme_bnd_site = None
        if "enzyme_bnd_site" in json_data.keys() and\
           json_data["enzyme_bnd_site"] is not None:
            enzyme_bnd_site = Site.from_json(
                json_data["enzyme_bnd_site"])

        substrate_bnd_region = None
        if "substrate_bnd_region" in json_data.keys() and\
           json_data["substrate_bnd_region"] is not None:
            substrate_bnd_region = Region.from_json(
                json_data["substrate_bnd_region"])

        substrate_bnd_site = None
        if "substrate_bnd_site" in json_data.keys() and\
           json_data["substrate_bnd_site"] is not None:
            substrate_bnd_site = Site.from_json(
                json_data["substrate_bnd_site"])

        rate = None
        if "rate" in json_data.keys():
            rate = json_data["rate"]
        annotation = None
        if "annotation" in json_data.keys():
            annotation = json_data["annotation"]
        desc = None
        if "desc" in json_data.keys():
            desc = json_data["desc"]

        return cls(
            enzyme, substrate, target, value=value,
            enzyme_bnd_subactor=enzyme_bnd_subactor,
            substrate_bnd_subactor=substrate_bnd_subactor,
            enzyme_bnd_region=enzyme_bnd_region,
            enzyme_bnd_site=enzyme_bnd_site,
            substrate_bnd_region=substrate_bnd_region,
            substrate_bnd_site=substrate_bnd_site,
            rate=rate, annotation=annotation, desc=desc)

    def generate_desc(self):
        """Generate text description of the interaction."""
        residue_rep = ""
        if isinstance(self.target, State):
            state_rep = self.target.generate_desc()
        else:
            state_rep = self.target.state.generate_desc()
            residue_rep = self.target.generate_desc()

        desc = "{} modifies the {} of the {}{} when bound".format(
            self.enzyme.generate_desc(), state_rep, self.substrate.generate_desc(),
            " at {}".format(residue_rep) if len(residue_rep) > 0 else "")
        return desc
