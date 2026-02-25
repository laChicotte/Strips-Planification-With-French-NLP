from itertools import permutations
from re import findall

# Constante pour le nombre maximum de passes de vérification des buts
MAX_GOAL_CHECK_PASSES = 5

# PREDICATS - SUR, SURTABLE, LIBRE, TENU, MAINVIDE
class PREDICATE:
  def __str__(self):
    pass
  def __repr__(self):
    pass
  def __eq__(self, other):
    pass
  def __hash__(self):
    pass
  def get_action(self, world_state):
    pass


#OPERATIONS (Actions) - Empiler, Dépiler, Prendre, Déposer
class Operation:
  def __str__(self):
    pass
  def __repr__(self):
    pass
  def __eq__(self, other):
    pass
  def precondition(self):
    pass
  def delete(self):
    pass
  def add(self):
    pass


class ON(PREDICATE):

  def __init__(self, X, Y):
    self.X = X
    self.Y = Y

  def __str__(self):
    return "ON({X},{Y})".format(X=self.X, Y=self.Y)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def __hash__(self):
    return hash(str(self))

  def get_action(self, world_state):
    return StackOp(self.X, self.Y)


class ONTABLE(PREDICATE):

  def __init__(self, X):
    self.X = X

  def __str__(self):
    return "ONTABLE({X})".format(X=self.X)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def __hash__(self):
    return hash(str(self))

  def get_action(self, world_state):
    return PutdownOp(self.X)


class CLEAR(PREDICATE):

  def __init__(self, X):
    self.X = X

  def __str__(self):
    return "CLEAR({X})".format(X=self.X)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def __hash__(self):
    return hash(str(self))

  def get_action(self, world_state):
    for predicate in world_state:
      # Si le bloc est sur un autre block, Dépiler
      if isinstance(predicate, ON) and predicate.Y == self.X:
        return UnstackOp(predicate.X, predicate.Y)
    return None


class HOLDING(PREDICATE):

  def __init__(self, X):
    self.X = X

  def __str__(self):
    return "HOLDING({X})".format(X=self.X)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def __hash__(self):
    return hash(str(self))

  def get_action(self, world_state):
    X = self.X
    # Si le bloc est sur la table, Prendre
    if ONTABLE(X) in world_state:
      return PickupOp(X)
    # Si le bloc est sur un autre block, Dépiler
    else:
      for predicate in world_state:
        if isinstance(predicate, ON) and predicate.X == X:
          return UnstackOp(X, predicate.Y)


class ARMEMPTY(PREDICATE):

  def __init__(self):
    pass

  def __str__(self):
    return "ARMEMPTY"

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def __hash__(self):
    return hash(str(self))

  # FIX: suppression de l'argument mutable par défaut (world_state=[])
  def get_action(self, world_state=None):
    if world_state is None:
      world_state = []
    for predicate in world_state:
      if isinstance(predicate, HOLDING):
        return PutdownOp(predicate.X)
    return None


class StackOp(Operation):

  def __init__(self, X, Y):
    self.X = X
    self.Y = Y

  def __str__(self):
    return "EMPILER({X},{Y})".format(X=self.X, Y=self.Y)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def precondition(self):
    return [CLEAR(self.Y), HOLDING(self.X)]

  def delete(self):
    return [CLEAR(self.Y), HOLDING(self.X)]

  def add(self):
    return [ARMEMPTY(), ON(self.X, self.Y), CLEAR(self.X)]


class UnstackOp(Operation):

  def __init__(self, X, Y):
    self.X = X
    self.Y = Y

  def __str__(self):
    return "DEPILER({X},{Y})".format(X=self.X, Y=self.Y)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def precondition(self):
    return [ARMEMPTY(), ON(self.X, self.Y), CLEAR(self.X)]

  def delete(self):
    return [ARMEMPTY(), ON(self.X, self.Y), CLEAR(self.X)]

  def add(self):
    return [CLEAR(self.Y), HOLDING(self.X)]


class PickupOp(Operation):

  def __init__(self, X):
    self.X = X

  def __str__(self):
    return "PRENDRE({X})".format(X=self.X)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def precondition(self):
    return [CLEAR(self.X), ONTABLE(self.X), ARMEMPTY()]

  def delete(self):
    return [CLEAR(self.X), ONTABLE(self.X), ARMEMPTY()]

  def add(self):
    return [HOLDING(self.X)]


class PutdownOp(Operation):

  def __init__(self, X):
    self.X = X

  def __str__(self):
    return "DEPOSER({X})".format(X=self.X)

  def __repr__(self):
    return self.__str__()

  def __eq__(self, other):
    return self.__dict__ == other.__dict__ and self.__class__ == other.__class__

  def precondition(self):
    return [HOLDING(self.X)]

  def delete(self):
    return [HOLDING(self.X)]

  def add(self):
    return [ARMEMPTY(), ONTABLE(self.X), CLEAR(self.X)]


def isPredicate(obj):
  return isinstance(obj, PREDICATE)

def isOperation(obj):
  return isinstance(obj, Operation)

def arm_status(world_state):
  for predicate in world_state:
    if isinstance(predicate, HOLDING):
      return predicate
  return ARMEMPTY()


class GoalStackPlanner:

  def __init__(self, initial_state, goal_state):
    self.initial_state = initial_state
    self.goal_state = goal_state

  def get_steps(self):

    # Initier la liste qui contiendra le plan
    steps = []

    # Initier la pile des buts
    stack = []

    # Copie de l'état initial dans l'état courant
    world_state = self.initial_state.copy()

    # Mettre le but dans la pile
    stack.append(self.goal_state.copy())

    # Repeter tant que la pile des buts n'est pas vide
    pass_count = 0
    while len(stack) != 0:

      # Recuperer le sommet de la pile
      stack_top = stack[-1]

      # Si le sommet de pile est un but composé, mettre les buts insatisfaits dans la pile
      if type(stack_top) is list:
        compound_goal = stack.pop()
        for goal in compound_goal:
          if goal not in world_state:
            stack.append(goal)

      # Si le sommet de pile est une opération (Action)
      elif isOperation(stack_top):

        operation = stack[-1]
        all_preconditions_satisfied = True

        # FIX: utiliser precondition() au lieu de delete() pour vérifier les préconditions
        for predicate in operation.precondition():
          if predicate not in world_state:
            all_preconditions_satisfied = False
            stack.append(predicate)

        # Si toutes les preconditions sont satisfaites, retirer l'action de la pile et l'executer
        if all_preconditions_satisfied:

          stack.pop()
          steps.append(operation)

          for predicate in operation.delete():
            world_state.remove(predicate)
          for predicate in operation.add():
            world_state.append(predicate)

      # Si le sommet de pile est un but simple satisfait
      elif stack_top in world_state:
        stack.pop()

      # Si le sommet de la pile est un but simple non satisfait
      else:
        unsatisfied_goal = stack.pop()

        # Remplacer le but non satisfait par une action qui le complete
        action = unsatisfied_goal.get_action(world_state)

        # FIX: vérifier que get_action a trouvé une action applicable
        if action is None:
          return steps, world_state

        stack.append(action)
        # Ajouter les préconditions non satisfaites dans la pile
        for predicate in action.precondition():
          if predicate not in world_state:
            stack.append(predicate)

      # A la fin d'une resolution, verifier si tous les buts sont resolus
      # sinon injecter les buts non resolus et reprendre
      if len(stack) == 0 and pass_count <= MAX_GOAL_CHECK_PASSES:
        pass_count += 1
        for goal in self.goal_state:
          if goal not in world_state:
            stack.append(goal)

    return steps, world_state


def transform_goal(chaine):
    # Utiliser une expression régulière pour trouver les paires de caractères entre parenthèses
    paires = findall(r'\((.*?)\)', chaine)

    for paire in paires:
        if ',' in paire:
          # Remplacer chaque paire complexe ON et entourer ses arguments
          before, after = paire.split(',')
          chaine = chaine.replace(f"ON({before},{after})", f"ON('{before}','{after}')")
        else:
          # Remplacer chaque paire simple par une chaîne entourée de guillemets simples
          chaine = chaine.replace(f"({paire})", f"('{paire}')")
    chaine = chaine.replace('ARMEMPTY', 'ARMEMPTY()')
    return chaine


def read_state_from_file(filename):
    """Lit l'état depuis un fichier.
    Note: utilise eval() car le fichier contient des constructeurs Python (ON, ONTABLE, etc.)
    Ne jamais utiliser avec des fichiers non fiables."""
    try:
        with open(filename, 'r') as file:
            content = file.read().strip()
            if not content:
                return []
            state = eval(content)
        return state
    except (SyntaxError, NameError, FileNotFoundError) as e:
        print(f"Erreur lors de la lecture de {filename}: {e}")
        return []


def read_goal_from_file(filename):
    """Lit le but depuis un fichier.
    Note: utilise eval() car le fichier contient des constructeurs Python (ON, ONTABLE, etc.)
    Ne jamais utiliser avec des fichiers non fiables."""
    try:
        with open(filename, 'r') as file:
            content = file.read().strip()
            if not content:
                return []
            state = eval(content)
        return state
    except (SyntaxError, NameError, FileNotFoundError) as e:
        print(f"Erreur lors de la lecture de {filename}: {e}")
        return []


def write_state_to_file(filename, state):
    with open(filename, 'w') as file:
        file.write(state)


def cleanStackUnstack(rep):
  cleaned_steps = []
  i = 0
  while i < len(rep):
      if (i < len(rep) - 1
          and isinstance(rep[i], StackOp)
          and isinstance(rep[i + 1], UnstackOp)
          and rep[i].X == rep[i + 1].X
          and rep[i].Y == rep[i + 1].Y):
          i += 2
          continue
      cleaned_steps.append(rep[i])
      i += 1
  return cleaned_steps


def cleanPickPut(rep):
  cleaned_steps = []
  i = 0
  while i < len(rep):
      if (i < len(rep) - 1
          and isinstance(rep[i], PickupOp)
          and isinstance(rep[i + 1], PutdownOp)
          and rep[i].X == rep[i + 1].X):
          i += 2
          continue
      cleaned_steps.append(rep[i])
      i += 1
  return cleaned_steps


def ask_for_plan(initial_state, goal_state):
  steps = []

  # FIX: variables renommées pour éviter le shadowing de la boucle externe
  for perm in permutations(goal_state):
    goal_stack = GoalStackPlanner(initial_state=initial_state, goal_state=list(perm))
    step, world = goal_stack.get_steps()

    initial_goal = [str(g) for g in goal_state]
    final_goal = [str(g) for g in world]

    if set(initial_goal).issubset(set(final_goal)):
      steps.append((step, world))

  if steps:
    # FIX: garder le world_state correspondant au meilleur plan
    best_step, best_world = min(steps, key=lambda x: len(x[0]))
    write_state_to_file('initial.tx', transform_goal(str(best_world)))
    best_step = cleanStackUnstack(best_step)
    best_step = cleanPickPut(best_step)
    return True, best_step, "Voici le but : "

  else:
    sms = "Le but est probablement impossible à réaliser verifiez la cohérence de votre demande"
    sms = sms + "\nPar exemple : Avoir A sur la table et en meme temps tenir A est impossible"
    return False, [], sms