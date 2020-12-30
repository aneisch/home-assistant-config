import "https://unpkg.com/vis-network@8.1.0/dist/vis-network.min.js?module";

function loadCSS(url) {
  const link = document.createElement("link");
  link.type = "text/css";
  link.rel = "stylesheet";
  link.href = url;
  document.head.appendChild(link);
}

class OZWNetworkVisualizationCard extends HTMLElement {
  constructor() {
    super();
    this.bufferTime = 1000 * 60 * 5; //5 minutes
    this.attachShadow({
      mode: "open",
    });
    this.networkOptions = {
      autoResize: true,
      height: "1000px",
      layout: {
        improvedLayout: true,
      },
      physics: {
        barnesHut: {
          springConstant: 0,
          avoidOverlap: 10,
          damping: 0.09,
        },
      },
      nodes: {
        font: {
          multi: "html",
        },
      },
      edges: {
        smooth: {
          type: "continuous",
          forceDirection: "none",
          roundness: 0.6,
        },
      },
    };
  }

  setConfig(config) {
    // get & keep card-config and hass-interface
    const root = this.shadowRoot;
    if (root.lastChild) root.removeChild(root.lastChild);

    this._config = Object.assign({}, config);
    if (!this._config.integration) {
      this._config.integration = "ozw";
    }

    console.log("Loading for integration: ", this._config.integration);

    // assemble html
    const card = document.createElement("ha-card");
    const content = document.createElement("div");

    this.filterdiv = document.createElement("div");
    this.filterdiv.style = "display: flex; align-items: center";

    this.filterlable = document.createElement("div");
    this.filterlable.innerHTML = "Search: ";

    this.filterinput = document.createElement("input");
    this.filterinput.placeholder = "Name, Node ID, Model, ...";

    this.filterdiv.appendChild(this.filterlable);
    this.filterdiv.appendChild(this.filterinput);
    card.appendChild(this.filterdiv);
    card.appendChild(content);

    this.device_registry = {};
    this.nodes = [];
    this.network = new vis.Network(content, {}, this.networkOptions);

    this.filterinput.oninput = function () {
      let filterednodes = this.nodes.filter((x) =>
        x.label.toLowerCase().match(this.filterinput.value.toLowerCase())
      );
      this.network.selectNodes(filterednodes.map((x) => x.id));
    }.bind(this);

    root.appendChild(card);
  }

  _updateContent(data) {
    this._updateDevices(data.devices);
  }

  _updateDevices(devices) {
    this.nodes = [];
    var edges = [];

    devices.forEach((device) => {
      this.nodes.push({
        id: device.node_id,
        label: this._buildLabel(device),
        shape: this._getShape(device),
        mass: this._getMass(device),
        borderWidth: 3,
        color: {
          border: this._getBorderColor(device),
          background: "#ffffff",
          highlight: {
            border: this._getBorderColor(device),
            background: "#00fbff",
          },
        },
      });
      if (device.neighbors && device.neighbors.length > 0) {
        device.neighbors.forEach((neighbor) => {
          var idx = edges.findIndex(function (e) {
            return device.node_id === e.to && neighbor === e.from;
          });
          if (idx === -1) {
            edges.push({
              from: device.node_id,
              to: neighbor,
              label: "",
              color: { color: "#bfbfbf", highlight: "#00fbff" },
            });
          }
        });
      }
    });

    this.network.setData({ nodes: this.nodes, edges: edges });
  }

  _getBorderColor(device) {
    var avertage_rtt = Math.round(
      (parseInt(device.statistics.average_request_rtt) +
        parseInt(device.statistics.average_response_rtt)) /
        2.0
    );

    if (avertage_rtt === 0) {
      return "#ababab";
    } else if (avertage_rtt > 1000) {
      return "#ab0000";
    } else if (avertage_rtt > 500) {
      return "#e6b402";
    }
    return "#17ab00";
  }

  _getMass(device) {
    if (device.node_basic_string === "Static Controller") {
      return 2;
    } else if (device.node_basic_string === "Routing Slave") {
      return 4;
    } else {
      return 5;
    }
  }

  _getShape(device) {
    if (device.node_basic_string === "Static Controller") {
      return "box";
    } else if (device.node_basic_string === "Routing Slave") {
      return "ellipse";
    } else {
      return "circle";
    }
  }

  _buildLabel(device) {
    const regDevice = this.device_registry[device.ozw_instance][device.node_id];
    const name = regDevice ? regDevice.name_by_user || regDevice.name : "???";
    const model = regDevice ? regDevice.model : "";
    const avertage_rtt = Math.round(
      (parseInt(device.statistics.average_request_rtt) +
        parseInt(device.statistics.average_response_rtt)) /
        2.0
    );

    var res = "<b>" + name + "</b>\n";
    res += "<b>Model: </b>" + model + "\n";
    res += "<b>Node: </b>" + device.node_id + "\n";
    res += "<b>RTT: </b>" + avertage_rtt + " | ";
    res +=
      "<b>Send Count: </b>" +
      device.statistics.send_count +
      " (" +
      device.statistics.sent_failed +
      " failed)" +
      "\n";
    if ("is_routing" in device) {
      res += (device.is_routing ? "Routing" : "Not routing") + " | ";
    }
    if ("is_awake" in device) {
      res += (device.is_awake ? "Awake" : "Sleeping") + " | ";
    }
    if ("is_beaming" in device) {
      res += (device.is_beaming ? "Beaming" : "Not beaming") + "";
    }
    if (device.is_failed) {
      res += "\n<b>DEVICE FAILED</b>";
    }
    return res;
  }

  _ozwFetchNodeStatistics(hass, node) {
    return hass
      .callWS({
        type: "ozw/node_statistics",
        ozw_instance: node.ozw_instance,
        node_id: node.node_id,
      })
      .then((node_stat) => {
        node.statistics = node_stat;
      });
  }

  _ozwFetchInstanceNodes(hass, instance) {
    hass
      .callWS({
        type: "ozw/get_nodes",
        ozw_instance: instance,
      })
      .then((nodes) => {
        const stats_promises = [];
        nodes.forEach((node) => {
          stats_promises.push(this._ozwFetchNodeStatistics(hass, node));
        });

        Promise.all(stats_promises).then((node_stats_list) => {
          console.log(nodes);
          this._updateContent({ devices: nodes });
        });
      });
  }

  _getNodeIdFromRegistry(device) {
    if (this._config.integration === "zwave2mqtt") {
      const regIdentifiers = device.identifiers.find(
        (identifier) =>
          identifier[0] === "mqtt" && identifier[1].includes("zwave2mqtt")
      );
      if (!regIdentifiers) {
        return null;
      }

      const identifiers = regIdentifiers[1].split("_");
      const z2m_instance = 0;
      const node_id = identifiers[2].replace("node", "");

      return [z2m_instance, node_id];
    } else {
      const regIdentifiers = device.identifiers.find(
        (identifier) => identifier[0] === "ozw"
      );
      if (!regIdentifiers) {
        return null;
      }

      const identifiers = regIdentifiers[1].split(".");
      const ozw_instance = identifiers[0];
      const node_id = identifiers[1];

      return [ozw_instance, node_id];
    }
  }

  _updateDeviceRegistry(device_registry) {
    let node_set = new Set();
    device_registry.forEach((device) => {
      //const [zw_instance, node_id] = this._getNodeIdFromRegistry(device);
      const instance_node_id = this._getNodeIdFromRegistry(device);
      if (!instance_node_id) {
        return;
      }
      const zw_instance = instance_node_id[0];
      const node_id = instance_node_id[1];
      const instance_node_id_str = zw_instance + "." + node_id;
      if (node_set.has(instance_node_id_str)) {
        return;
      }
      node_set.add(instance_node_id_str);

      if (this.device_registry[zw_instance] === undefined) {
        this.device_registry[zw_instance] = {};
      }
      this.device_registry[zw_instance][node_id] = device;
    });
  }

  _loadOzw(hass) {
    hass
      .callWS({
        type: "ozw/get_instances",
      })
      .then((instances) => {
        instances.forEach((instance) => {
          // TODO: fix multi instance. ATM the last instance will win.
          this._ozwFetchInstanceNodes(hass, instance.ozw_instance);
        });
      })
      .catch((error) => {
        console.warn("Failed to get instances: ", error.message);
      });
  }

  _loadZ2m(hass) {
    class Deferred {
      constructor() {
        var self = this;
        this.promise = new Promise(function (resolve, reject) {
          self.reject = reject;
          self.resolve = resolve;
        });
      }
    }

    class Z2MStatsReceiver {
      constructor() {
        this.stats_dfd = new Deferred();
        this.node_ids = [];
        this.node_stats = {};

        var self = this;
        hass.connection.subscribeMessage(
          (message) => {
            if (!self.node_ids) return;
            if (!message.payload) return;

            const payload = JSON.parse(message.payload);
            const node_id = payload.args[0];

            const index = self.node_ids.indexOf(node_id);
            if (index < 0) return;
            self.node_ids.splice(index, 1);
            self.node_stats[node_id] = payload.result;

            if (self.node_ids.length == 0) {
              self.stats_dfd.resolve(self.node_stats);
            }
          },
          {
            type: "mqtt/subscribe",
            topic: "z2m/_CLIENTS/ZWAVE_GATEWAY-HA/api/getNodeStatistics",
          }
        );
      }

      start(node_ids) {
        this.node_ids.push(...node_ids);
        this.node_stats = {};
        node_ids.forEach((id) => {
          hass.callService("mqtt", "publish", {
            topic: "z2m/_CLIENTS/ZWAVE_GATEWAY-HA/api/getNodeStatistics/set",
            payload: `{ "args": [${id}] }`,
          });
        });
        return this.stats_dfd.promise;
      }
    }

    hass.callService("mqtt", "publish", {
      topic: "z2m/_CLIENTS/ZWAVE_GATEWAY-HA/api/refreshNeighborns/set",
    });

    var stats_receiver = new Z2MStatsReceiver();

    const neighbors_cb = (message) => {
      if (!message.payload) return;
      const neighbors_array = JSON.parse(message.payload).result;

      const nodes = [];
      neighbors_array.forEach((neighbors, index) => {
        if (!neighbors) {
          return;
        }
        nodes.push({
          ozw_instance: 0,
          node_id: index,
          neighbors: neighbors,
          statistics: {
            average_request_rtt: 999999,
            average_response_rtt: 999999,
          },
          node_basic_string:
            index === 1 ? "Static Controller" : "Routing Slave",
        });
      });

      stats_receiver
        .start(
          nodes.map((node) => {
            return node.node_id;
          })
        )
        .then((stats) => {
          console.log(stats);
          nodes.forEach((node) => {
            if (!node.node_id in stats) return;
            const node_stats = stats[node.node_id];
            node.statistics.average_request_rtt = node_stats.averageRequestRTT;
            node.statistics.average_response_rtt =
              node_stats.averageResponseRTT;
            node.statistics.send_count = node_stats.sentCnt;
            node.statistics.sent_failed = node_stats.sentFailed;
          });
          this._updateContent({ devices: nodes });
        });
    };

    // wait a bit to avoid getting an old refreshNeighborns topic
    setTimeout(() => {
      hass.connection.subscribeMessage(neighbors_cb, {
        type: "mqtt/subscribe",
        topic: "z2m/_CLIENTS/ZWAVE_GATEWAY-HA/api/refreshNeighborns/#",
      });
    }, 100);
  }

  set hass(hass) {
    if (
      this.lastUpdated &&
      new Date(this.lastUpdated + this.bufferTime) > Date.now()
    ) {
      return;
    }

    hass
      .callWS({
        type: "config/device_registry/list",
      })
      .then((device_registry) => {
        this._updateDeviceRegistry(device_registry);

        if (this._config.integration === "zwave2mqtt") {
          this._loadZ2m(hass);
        } else {
          this._loadOzw(hass);
        }
      });

    this.lastUpdated = Date.now();
  }

  getCardSize() {
    return 10;
  }
}

customElements.define(
  "ozw-network-visualization-card",
  OZWNetworkVisualizationCard
);
