from otree.api import *
import random

doc = """
Treatment 2: Tax Frame. 
Features: Implicit Partner pairing, Noisy Signaling, 
Dynamic Candidate Voting, and Partner-Aware Dynamic Labels.
"""


class C(BaseConstants):
    NAME_IN_URL = 'T2_coalition_tax'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = 10
    ENDOWMENT_TAX = 120
    TAX_AMOUNT = 20
    BUDGET = 100
    OFFICE_BONUS = 50
    SIGNAL_THRESHOLD_LOW = 40
    SIGNAL_THRESHOLD_HIGH = 70
    NOISE_MEAN = 0
    NOISE_SD = 10
    VOTE_WEIGHT = 10
    PAYOFF_LOW = 15
    PAYOFF_MED = 25
    PAYOFF_HIGH = 30


class Subsession(BaseSubsession):
    pass

def creating_session(subsession):
    if subsession.round_number == 1:
        for group in subsession.get_groups():
            players = group.get_players()
            partners = random.sample(players, 2)
            for p in players:
                p.is_connected = (p in partners)

            initial_incumbent = random.choice(players)
            initial_incumbent.is_incumbent = True
    else:
        # Copy is_connected from round 1 for every player.
        # This is necessary because oTree re-initializes player fields
        # with their initial= defaults when creating each new subsession,
        # which overwrites any values set during round 1's creating_session.
        for group in subsession.get_groups():
            for p in group.get_players():
                p.is_connected = p.in_round(1).is_connected


class Group(BaseGroup):
    incumbent_id = models.IntegerField()
    public_investment = models.IntegerField(label="Tokens for Group Project (P)", min=0, max=100, initial=0)
    npi = models.FloatField()
    public_signal = models.StringField()
    current_pg_payoff = models.IntegerField()
    h_to_p1 = models.IntegerField(min=0, max=100, initial=0)
    h_to_p2 = models.IntegerField(min=0, max=100, initial=0)
    h_to_p3 = models.IntegerField(min=0, max=100, initial=0)
    h_to_p4 = models.IntegerField(min=0, max=100, initial=0)
    h_to_p5 = models.IntegerField(min=0, max=100, initial=0)
    private_rents = models.IntegerField(min=0)
    election_winner_id = models.IntegerField()


class Player(BasePlayer):
    is_incumbent = models.BooleanField(initial=False)
    is_connected = models.BooleanField(initial=False)
    transfer_received = models.IntegerField(initial=0)
    interim_payoff = models.IntegerField(initial=0)
    is_candidate = models.BooleanField(
        label="Do you want to run for office?",
        choices=[[True, 'Yes'], [False, 'No']],
        initial=False
    )
    campaign_effort = models.IntegerField(label="Campaign Effort:", min=0, initial=0)
    vote_choice = models.IntegerField()
    votes_received = models.IntegerField(initial=0)
    election_tickets = models.IntegerField(initial=0)


# --- PAGES ---

class GenInstructions(Page):
    @staticmethod
    def is_displayed(player): return player.round_number == 1


class InstructionWaitPage(WaitPage):
    template_name = 'T2_coalition_tax/InstructionWaitPage.html'

    @staticmethod
    def after_all_players_arrive(group: Group):
        incumbent = [p for p in group.get_players() if p.is_incumbent][0]
        group.incumbent_id = incumbent.id_in_group


class SpecificInstructions(Page):
    @staticmethod
    def is_displayed(player): return player.round_number == 1


class PartnerRevelation(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.is_connected and player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        partner = [p for p in player.group.get_players() if p.is_connected and p != player][0]
        return {'partner_id': partner.id_in_group}


class PartnerWaitPage(WaitPage):
    template_name = 'T2_coalition_tax/PartnerWaitPage.html'


class Allocation(Page):
    form_model = 'group'

    @staticmethod
    def is_displayed(player: Player):
        return player.is_incumbent

    @staticmethod
    def get_form_fields(player: Player):
        all_h = ['h_to_p1', 'h_to_p2', 'h_to_p3', 'h_to_p4', 'h_to_p5']
        return ['public_investment'] + [f for f in all_h if f != f'h_to_p{player.id_in_group}']

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        transfers = []
        for i in range(1, 6):
            if i == player.id_in_group: continue
            target = group.get_player_by_id(i)
            label_text = "Transfer to Your Partner" if (
                player.is_connected and target.is_connected) else f"Transfer to Player {i}"
            transfers.append({'field_name': f'h_to_p{i}', 'label': label_text})
        return {'transfer_fields': transfers}


class AllocationWaitPage(WaitPage):
    template_name = 'T2_coalition_tax/AllocationWaitPage.html'

    @staticmethod
    def after_all_players_arrive(group: Group):
        players = group.get_players()
        h_values = {1: group.h_to_p1, 2: group.h_to_p2, 3: group.h_to_p3, 4: group.h_to_p4, 5: group.h_to_p5}
        total_h = sum(h_values[p.id_in_group] for p in players if not p.is_incumbent)
        group.private_rents = C.BUDGET - group.public_investment - total_h
        group.npi = group.public_investment + random.normalvariate(C.NOISE_MEAN, C.NOISE_SD)

        if group.npi < C.SIGNAL_THRESHOLD_LOW:
            group.public_signal, group.current_pg_payoff = "Low", C.PAYOFF_LOW
        elif group.npi < C.SIGNAL_THRESHOLD_HIGH:
            group.public_signal, group.current_pg_payoff = "Medium", C.PAYOFF_MED
        else:
            group.public_signal, group.current_pg_payoff = "High", C.PAYOFF_HIGH

        for p in players:
            p.interim_payoff = (C.ENDOWMENT_TAX - C.TAX_AMOUNT) + group.current_pg_payoff
            if p.is_incumbent:
                p.interim_payoff += group.private_rents + C.OFFICE_BONUS
            else:
                p.transfer_received = h_values[p.id_in_group]
                p.interim_payoff += p.transfer_received


class Candidacy(Page):
    form_model = 'player'
    form_fields = ['is_candidate', 'campaign_effort']

    @staticmethod
    def is_displayed(player: Player): return not player.is_incumbent

    @staticmethod
    def vars_for_template(player: Player):
        incumbent = [p for p in player.group.get_players() if p.is_incumbent][0]
        return {
            'incumbent_is_partner': (player.is_connected and incumbent.is_connected),
            'vote_weight': C.VOTE_WEIGHT
        }

    @staticmethod
    def error_message(player: Player, values):
        if values['campaign_effort'] > player.interim_payoff:
            return f"You cannot spend more tokens than you have ({player.interim_payoff})."


class BallotWaitPage(WaitPage):
    template_name = 'T2_coalition_tax/BallotWaitPage.html'

    @staticmethod
    def after_all_players_arrive(group: Group):
        candidates = [p for p in group.get_players() if p.is_candidate and not p.is_incumbent]
        if not candidates:
            random.choice([p for p in group.get_players() if not p.is_incumbent]).is_candidate = True


class Voting(Page):
    form_model = 'player'
    form_fields = ['vote_choice']

    @staticmethod
    def vars_for_template(player: Player):
        candidates_list = []
        for p in player.group.get_players():
            if p.is_candidate and not p.is_incumbent:
                if p == player:
                    label = "Yourself"
                elif p.is_connected and player.is_connected:
                    label = f"Player {p.id_in_group} (Your Partner)"
                else:
                    label = f"Player {p.id_in_group}"
                candidates_list.append({'id': p.id_in_group, 'label': label})
        return {
            'candidates': candidates_list,
            'vote_weight': C.VOTE_WEIGHT
        }


class ElectionWaitPage(WaitPage):
    template_name = 'T2_coalition_tax/ElectionWaitPage.html'

    @staticmethod
    def after_all_players_arrive(group: Group):
        players = group.get_players()
        for p in players:
            if p.vote_choice:
                group.get_player_by_id(p.vote_choice).votes_received += 1
        candidates = [p for p in players if p.is_candidate and not p.is_incumbent]
        for c in candidates:
            c.election_tickets = (C.VOTE_WEIGHT * c.votes_received) + c.campaign_effort
        winner = random.choices(candidates, weights=[c.election_tickets + 0.1 for c in candidates], k=1)[0]
        group.election_winner_id = winner.id_in_group
        for p in players:
            p.payoff = p.interim_payoff - p.campaign_effort
            if group.round_number < C.NUM_ROUNDS:
                p.in_round(group.round_number + 1).is_incumbent = (p.id_in_group == winner.id_in_group)


class Results(Page):
    template_name = 'T2_coalition_tax/ElectionResults.html'

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        winner = group.get_player_by_id(group.election_winner_id)
        winner_label = f"Player {winner.id_in_group}"
        if winner == player:
            winner_label = "You"
        elif winner.is_connected and player.is_connected:
            winner_label = f"Player {winner.id_in_group} (your Partner)"
        return {
            'winner_label': winner_label,
            'winner_tickets': winner.election_tickets,
            'won_election': (player == winner)
        }


page_sequence = [
    GenInstructions, InstructionWaitPage, SpecificInstructions, PartnerRevelation, PartnerWaitPage,
    Allocation, AllocationWaitPage, Candidacy, BallotWaitPage, Voting, ElectionWaitPage, Results
]