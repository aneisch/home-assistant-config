""" The Simulated Annealing (recuit simulé) algorithm"""
import logging
import random
import math
import copy

from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)

DEBUG = False


class SimulatedAnnealingAlgorithm:
    """The class which implemenets the Simulated Annealing algorithm"""

    # Paramètres de l'algorithme de recuit simulé
    _temperature_initiale: float = 1000
    _temperature_minimale: float = 0.1
    _facteur_refroidissement: float = 0.95
    _nombre_iterations: float = 1000
    _equipements: list[ManagedDevice]
    _puissance_totale_eqt_initiale: float
    _cout_achat: float = 15  # centimes
    _cout_revente: float = 10  # centimes
    _taxe_revente: float = 10  # pourcentage
    _consommation_net: float
    _production_solaire: float

    def __init__(
        self,
        initial_temp: float,
        min_temp: float,
        cooling_factor: float,
        max_iteration_number: int,
    ):
        """Initialize the algorithm with values"""
        self._temperature_initiale = initial_temp
        self._temperature_minimale = min_temp
        self._facteur_refroidissement = cooling_factor
        self._nombre_iterations = max_iteration_number
        _LOGGER.info(
            "Initializing the SimulatedAnnealingAlgorithm with initial_temp=%.2f min_temp=%.2f cooling_factor=%.2f max_iterations_number=%d",
            self._temperature_initiale,
            self._temperature_minimale,
            self._facteur_refroidissement,
            self._nombre_iterations,
        )

    def recuit_simule(
        self,
        devices: list[ManagedDevice],
        power_consumption: float,
        solar_power_production: float,
        sell_cost: float,
        buy_cost: float,
        sell_tax_percent: float,
        battery_soc: float,
        priority_weight: int,
    ):
        """The entrypoint of the algorithm:
        You should give:
         - devices: a list of ManagedDevices. devices that are is_usable false are not taken into account
         - power_consumption: the current power consumption. Can be negeative if power is given back to grid.
         - solar_power_production: the solar production power
         - sell_cost: the sell cost of energy
         - buy_cost: the buy cost of energy
         - sell_tax_percent: a sell taxe applied to sell energy (a percentage)
         - battery_soc: the state of charge of the battery (0-100)
         - priority_weight: the weight of the priority in the cost calculation. 10 means 10%

         In return you will have:
          - best_solution: a list of object in whitch name, power_max and state are set,
          - best_objectif: the measure of the objective for that solution,
          - total_power_consumption: the total of power consumption for all equipments which should be activated (state=True)
        """
        if (
            len(devices) <= 0  # pylint: disable=too-many-boolean-expressions
            or power_consumption is None
            or solar_power_production is None
            or sell_cost is None
            or buy_cost is None
            or sell_tax_percent is None
        ):
            _LOGGER.info(
                "Not all informations are available for Simulated Annealign algorithm to work. Calculation is abandoned"
            )
            return [], -1, -1

        _LOGGER.debug(
            "Calling recuit_simule with power_consumption=%.2f, solar_power_production=%.2f sell_cost=%.2f, buy_cost=%.2f, tax=%.2f%% devices=%s",
            power_consumption,
            solar_power_production,
            sell_cost,
            buy_cost,
            sell_tax_percent,
            devices,
        )
        self._cout_achat = buy_cost
        self._cout_revente = sell_cost
        self._taxe_revente = sell_tax_percent
        self._consommation_net = power_consumption
        self._production_solaire = solar_power_production
        self._priority_weight = priority_weight / 100.0  # to get percentage

        # fix #131 - costs cannot be negative or 0
        if self._cout_achat <= 0 or self._cout_revente <= 0:
            _LOGGER.warning(
                "The cost of energy cannot be negative or 0. Buy cost=%.2f, Sell cost=%.2f. Setting them to 1",
                self._cout_achat,
                self._cout_revente,
            )
            self._cout_achat = self._cout_revente = 1

        self._equipements = []
        for _, device in enumerate(devices):
            if not device.is_enabled:
                _LOGGER.debug("%s is disabled. Forget it", device.name)
                continue

            device.set_battery_soc(battery_soc)
            usable = device.is_usable
            waiting = device.is_waiting
            # Force deactivation if active, not usable and not waiting
            force_state = (
                False
                if device.is_active
                and ((not usable and not waiting) or device.current_power <= 0)
                else device.is_active
            )
            self._equipements.append(
                {
                    "power_max": device.power_max,
                    "power_min": device.power_min,
                    "power_step": device.power_step,
                    "current_power": device.current_power,  # if force_state else 0,
                    # Initial Requested power is the current power if usable
                    "requested_power": device.current_power,  # if force_state else 0,
                    "name": device.name,
                    "state": force_state,
                    "is_usable": device.is_usable,
                    "is_waiting": waiting,
                    "can_change_power": device.can_change_power,
                    "priority": device.priority,
                }
            )
        if DEBUG:
            _LOGGER.debug("enabled _equipements are: %s", self._equipements)

        # Générer une solution initiale
        solution_actuelle = self.generer_solution_initiale(self._equipements)
        meilleure_solution = solution_actuelle
        meilleure_objectif = self.calculer_objectif(solution_actuelle)
        temperature = self._temperature_initiale

        for _ in range(self._nombre_iterations):
            # Générer un voisin
            objectif_actuel = self.calculer_objectif(solution_actuelle)
            if DEBUG:
                _LOGGER.debug("Objectif actuel : %.2f", objectif_actuel)

            voisin = self.permuter_equipement(solution_actuelle)

            # Calculer les objectifs pour la solution actuelle et le voisin
            objectif_voisin = self.calculer_objectif(voisin)
            if DEBUG:
                _LOGGER.debug("Objectif voisin : %2.f", objectif_voisin)

            # Accepter le voisin si son objectif est meilleur ou si la consommation totale n'excède pas la production solaire
            if objectif_voisin < objectif_actuel:
                _LOGGER.debug("---> On garde l'objectif voisin")
                solution_actuelle = voisin
                if objectif_voisin < meilleure_objectif:
                    _LOGGER.debug("---> C'est la meilleure jusque là")
                    meilleure_solution = voisin
                    meilleure_objectif = objectif_voisin
            else:
                # Accepter le voisin avec une certaine probabilité
                probabilite = math.exp(
                    (objectif_actuel - objectif_voisin) / temperature
                )
                if (seuil := random.random()) < probabilite:
                    solution_actuelle = voisin
                    if DEBUG:
                        _LOGGER.debug(
                            "---> On garde l'objectif voisin car seuil (%.2f) inférieur à proba (%.2f)",
                            seuil,
                            probabilite,
                        )
                else:
                    if DEBUG:
                        _LOGGER.debug("--> On ne prend pas")

            # Réduire la température
            temperature *= self._facteur_refroidissement
            if DEBUG:
                _LOGGER.debug(" !! Temperature %.2f", temperature)
            if temperature < self._temperature_minimale or meilleure_objectif <= 0:
                break

        return (
            meilleure_solution,
            meilleure_objectif,
            self.consommation_equipements(meilleure_solution),
        )

    def calculer_objectif(self, solution) -> float:
        """Calcul de l'objectif : minimiser le surplus de production solaire
        rejets = 0 if consommation_net >=0 else -consommation_net
        consommation_solaire = min(production_solaire, production_solaire - rejets)
        consommation_totale = consommation_net + consommation_solaire
        """

        puissance_totale_eqt = self.consommation_equipements(solution)
        diff_puissance_totale_eqt = (
            puissance_totale_eqt - self._puissance_totale_eqt_initiale
        )

        new_consommation_net = self._consommation_net + diff_puissance_totale_eqt
        new_rejets = 0 if new_consommation_net >= 0 else -new_consommation_net
        new_import = 0 if new_consommation_net < 0 else new_consommation_net
        new_consommation_solaire = min(
            self._production_solaire, self._production_solaire - new_rejets
        )
        new_consommation_totale = (
            new_consommation_net + new_rejets
        ) + new_consommation_solaire
        if DEBUG:
            _LOGGER.debug(
                "Objectif : cette solution ajoute %.3fW a la consommation initial. Nouvelle consommation nette=%.3fW. Nouveaux rejets=%.3fW. Nouvelle conso totale=%.3fW",
                diff_puissance_totale_eqt,
                new_consommation_net,
                new_rejets,
                new_consommation_totale,
            )

        cout_revente_impose = self._cout_revente * (1.0 - self._taxe_revente / 100.0)
        coef_import = (self._cout_achat) / (self._cout_achat + cout_revente_impose)
        coef_rejets = (cout_revente_impose) / (self._cout_achat + cout_revente_impose)

        consumption_coef = coef_import * new_import + coef_rejets * new_rejets
        # calculate the priority coef as the sum of the priority of all devices
        # in the solution
        if puissance_totale_eqt > 0:
            priority_coef = sum((equip["priority"] * equip["requested_power"] / puissance_totale_eqt) for i, equip in enumerate(solution) if equip["state"])
        else:
            priority_coef = 0
        priority_weight = self._priority_weight

        ret = consumption_coef * (1.0 - priority_weight) + priority_coef * priority_weight
        return ret

    def generer_solution_initiale(self, solution):
        """Generate the initial solution (which is the solution given in argument) and calculate the total initial power"""
        self._puissance_totale_eqt_initiale = self.consommation_equipements(solution)
        return copy.deepcopy(solution)

    def consommation_equipements(self, solution):
        """The total power consumption for all active equipement"""
        return sum(
            equipement["requested_power"]
            for _, equipement in enumerate(solution)
            if equipement["state"]
        )

    def calculer_new_power(
        self, current_power, power_step, power_min, power_max, can_switch_off
    ):
        """Calcul une nouvelle puissance"""
        choices = []
        power_min_to_use = max(0, power_min - power_step) if can_switch_off else power_min

        # add all choices from current_power to power_min_to_use descending
        cp = current_power
        choice = -1
        while cp > power_min_to_use:
            cp -= power_step
            choices.append(choice)
            choice -= 1

        # if current_power > power_min_to_use:
        #    choices.append(-1)

        # add all choices from current_power to power_max ascending
        cp = current_power
        choice = 1
        while cp < power_max:
            cp += power_step
            choices.append(choice)
            choice += 1
        # if current_power < power_max:
        #     choices.append(1)

        if len(choices) <= 0:
            # No changes
            return current_power

        power_add = random.choice(choices) * power_step
        _LOGGER.debug("Adding %d power to current_power (%d)", power_add, current_power)
        requested_power = current_power + power_add
        _LOGGER.debug("New requested_power is %s", requested_power)
        return requested_power

    def permuter_equipement(self, solution):
        """Permuter le state d'un equipement eau hasard"""
        voisin = copy.deepcopy(solution)

        usable = [eqt for eqt in voisin if eqt["is_usable"]]

        if len(usable) <= 0:
            return voisin

        eqt = random.choice(usable)

        # name = eqt["name"]
        state = eqt["state"]
        can_change_power = eqt["can_change_power"]
        is_waiting = eqt["is_waiting"]

        # Current power is the last requested_power
        current_power = eqt.get("requested_power")
        power_max = eqt.get("power_max")
        power_step = eqt.get("power_step")
        if can_change_power:
            power_min = eqt.get("power_min")
        else:
            # If power is not manageable, min = max
            power_min = power_max

        # On veut gérer le is_waiting qui interdit d'allumer ou éteindre un eqt usable.
        # On veut pouvoir changer la puissance si l'eqt est déjà allumé malgré qu'il soit waiting.
        # Usable veut dire qu'on peut l'allumer/éteindre OU qu'on peut changer la puissance

        # if not can_change_power and is_waiting:
        #    -> on ne fait rien (mais ne devrait pas arriver car il ne serait pas usable dans ce cas)
        #
        # if state and can_change_power and is_waiting:
        #    -> change power mais sans l'éteindre (requested_power >= power_min)
        #
        # if state and can_change_power and not is_waiting:
        #    -> change power avec extinction possible
        #
        # if not state and not is_waiting
        #    -> allumage
        #
        # if state and not is_waiting
        #    -> extinction
        #
        if (not can_change_power and is_waiting) or (
            not state and can_change_power and is_waiting
        ):
            _LOGGER.debug("not can_change_power and is_waiting -> do nothing")
            return voisin

        if state and can_change_power and is_waiting:
            # calculated a new power but do not switch off (because waiting)
            requested_power = self.calculer_new_power(
                current_power, power_step, power_min, power_max, can_switch_off=False
            )
            assert (
                requested_power > 0
            ), "Requested_power should be > 0 because is_waiting is True"

        elif state and can_change_power and not is_waiting:
            # change power and accept switching off
            requested_power = self.calculer_new_power(
                current_power, power_step, power_min, power_max, can_switch_off=True
            )
            if requested_power < power_min:
                # deactivate the equipment
                eqt["state"] = False
                requested_power = 0

        elif not state and not is_waiting:
            # Allumage
            eqt["state"] = not state
            requested_power = power_min

        elif state and not is_waiting:
            # Extinction
            eqt["state"] = not state
            requested_power = 0

        elif "requested_power" not in locals():
            _LOGGER.error("We should not be there. eqt=%s", eqt)
            assert False, "Requested power n'a pas été calculé. Ce n'est pas normal"

        eqt["requested_power"] = requested_power

        if DEBUG:
            _LOGGER.debug(
                "      -- On permute %s puissance max de %.2f. Il passe à %s",
                eqt["name"],
                eqt["requested_power"],
                eqt["state"],
            )
        return voisin
