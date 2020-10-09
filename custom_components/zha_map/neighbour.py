import enum
import logging

import attr
import zigpy.zdo.types as zdo_t

from .helpers import LogMixin

LOGGER = logging.getLogger(__name__)


class NeighbourType(enum.IntEnum):
    Coordinator = 0x0
    Router = 0x1
    End_Device = 0x2
    Unknown = 0x3


@attr.s
class Neighbour(LogMixin):
    ieee = attr.ib(default=None)
    nwk = attr.ib(default=None)
    lqi = attr.ib(default=None)
    pan_id = attr.ib(default=None)
    device_type = attr.ib(default="unk")
    rx_on_when_idle = attr.ib(default=None)
    relation = attr.ib(default=None)
    new_joins_accepted = attr.ib(default=None)
    depth = attr.ib(default=None)
    device = attr.ib(default=None)
    model = attr.ib(default=None)
    manufacturer = attr.ib(default=None)
    neighbours = attr.ib(factory=list)
    offline = attr.ib(factory=bool)
    supported = attr.ib(default=True)

    @classmethod
    def new_from_record(cls, record):
        """Create new neighbour from a neighbour record."""

        r = cls()
        r.offline = False
        r.pan_id = str(record.extended_pan_id)
        r.ieee = record.ieee

        r.device_type = record.device_type.name
        r.rx_on_when_idle = record.rx_on_when_idle.name
        if record.relationship == zdo_t.Neighbor.RelationShip.NoneOfTheAbove:
            r.relation = "None_of_the_above"
        else:
            r.relation = record.relationship.name
        r.new_joins_accepted = record.permit_joining.name
        r.depth = record.depth
        r.lqi = record.lqi
        return r

    def _update_info(self):
        """Update info based on device information."""
        if self.device is None:
            return
        self.nwk = "0x{:04x}".format(self.device.nwk)
        self.model = self.device.model
        self.manufacturer = self.device.manufacturer
        if self.device.node_desc.is_valid:
            self.device_type = self.device.node_desc.logical_type.name
        else:
            self.device_type = "unknown"

    @classmethod
    async def scan_device(cls, device):
        """New neighbour from a scan."""
        r = cls()
        r.offline = False
        r.device = device
        r.ieee = device.ieee
        r._update_info()

        await r.scan()
        return r

    async def scan(self):
        """Scan for neighbours."""
        for neighbor in self.device.neighbors:
            new = self.new_from_record(neighbor.neighbor)
            try:
                new.device = self.device.application.get_device(new.ieee)
                new._update_info()
            except KeyError:
                self.warning("neighbour %s is not in 'zigbee.db'", new.ieee)

            self.neighbours.append(new)
        self.debug("Done scanning. Total %s neighbours", len(self.neighbours))

    def log(self, level, msg, *args):
        """Log a message with level."""
        msg = "[%s]: " + msg
        args = (self.device.ieee,) + args
        LOGGER.log(level, msg, *args)

    def json(self):
        """Return JSON representation of the neighbours table."""
        res = []
        for nei in sorted(self.neighbours, key=lambda x: x.ieee):
            if nei.device is not None:
                assert nei.ieee == nei.device.ieee
            dict_nei = attr.asdict(
                nei,
                filter=lambda a, v: a.name not in ("device", "neighbours"),
                retain_collection_types=True,
            )
            dict_nei["ieee"] = str(dict_nei["ieee"])
            res.append(dict_nei)
        return {
            "ieee": str(self.ieee),
            "nwk": self.nwk,
            "lqi": self.lqi,
            "device_type": self.device_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "offline": self.offline,
            "neighbours": res,
        }
