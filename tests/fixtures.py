"""Small hand-written PDDL used across the test suite."""

TOY_DOMAIN = """
(define (domain toy)
  (:requirements :strips :typing)
  (:types robot room)
  (:predicates
    (at ?r - robot ?x - room)
    (connected ?x - room ?y - room)
    (carrying ?r - robot)
    (clean ?x - room))
  (:action move
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (and (at ?r ?from) (connected ?from ?to))
    :effect (and (not (at ?r ?from)) (at ?r ?to)))
  (:action tidy
    :parameters (?r - robot ?x - room)
    :precondition (and (at ?r ?x) (not (carrying ?r)))
    :effect (clean ?x)))
"""

TOY_PROBLEM = """
(define (problem toy1)
  (:domain toy)
  (:objects r1 - robot a b - room)
  (:init (at r1 a) (connected a b) (connected b a))
  (:goal (and (at r1 b) (clean b))))
"""
