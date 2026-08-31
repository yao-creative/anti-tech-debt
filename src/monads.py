from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, Union

# Monads
T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E


Result = Union[Ok[T], Err[E]]


# map_ok:(T→U)→(Result[T,E]→Result[U,E])
def map_ok(r: Result[T, E], f: Callable[[T], U]) -> Result[U, E]:
    match r:
        case Ok(value=v):
            return Ok(f(v))
        case Err() as e:
            return e

# Set theory formalization of bind:
#
# Let T, U be sets (types of successful values), and E a set (type of error values).
# Let Result[T, E] = Ok(T) ∪ Err(E).
#
# bind : Result[T, E] × (T → Result[U, E]) → Result[U, E]
#
# For r ∈ Result[T, E], and f: T → Result[U, E],
#   bind(r, f) =
#     { f(v)       if r = Ok(v) for some v ∈ T
#     { Err(e)     if r = Err(e) for some e ∈ E
#
# In set notation:
#   ∀r ∈ (Ok(T) ∪ Err(E)), ∀f: T → (Ok(U) ∪ Err(E)),
#   bind(r, f) =
#     if ∃v ∈ T, r = Ok(v), then f(v)
#     else if ∃e ∈ E, r = Err(e), then Err(e)


def bind(r: Result[T, E], f: Callable[[T], Result[U, E]]) -> Result[U, E]:
    match r:
        case Ok(value=v):
            return f(v)
        case Err() as e:
            return e


# Set Theory Formalization of catching:
#
# Let T be the set of all possible return values of f (the function being called).
# Let E be the set of all possible error values produced by error (the error mapping function).
# Let Exc be the set of all Exceptions that can be raised by f().
#
# Define function f: () → T ∪ Exc
# Define function error: Exc → E
#
# The catching combinator can be defined as:
#
# catching(f, error): () → Result[T, E]
#   = { Ok(f())      if f() ∈ T (i.e., f() returns a value without raising)
#     { Err(error(e)) if f() raises e ∈ Exc
#
# In set notation:
# catching(f, error) ∈ (T ∪ Exc) → (Ok(T) ∪ Err(E))
#   where:
#      Ok: T → Ok(T)
#      Err: E → Err(E)
#
# More succinctly:
#   ∀f: () → T ∪ Exc,
#   ∀error: Exc → E,
#   catching(f, error) = 
#     if ∃t ∈ T, f() = t, then Ok(t)
#     else if ∃e ∈ Exc, f() raises e, then Err(error(e))
#
def catching(
    f: Callable[[], T],
    error: Callable[[Exception], E],
) -> Result[T, E]:
    try:
        return Ok(f())
    except Exception as exc:
        return Err(error(exc))

# Set Theory Formalization of map_err:
#
# Let T be the set of all possible Ok values.
# Let E be the set of all possible Err values.
# Let U be the set of all possible values returned by f (the error mapping function).
#
# Define function f: E → U
#
# The map_err combinator can be defined as:
#
# map_err(r, f): (Ok(T) ∪ Err(E)), f: E → U → (Ok(T) ∪ Err(U))
#   = { Ok(v)    if r = Ok(v) for some v ∈ T
#     { Err(f(e)) if r = Err(e) for some e ∈ E
#
# In set notation:
# map_err: (Ok(T) ∪ Err(E)) × (E → U) → (Ok(T) ∪ Err(U))
#   ∀r ∈ (Ok(T) ∪ Err(E)), ∀f: E → U,
#     map_err(r, f) = 
#       if ∃v ∈ T, r = Ok(v), then Ok(v)
#       else if ∃e ∈ E, r = Err(e), then Err(f(e))
def map_err(
    r: Result[T, E],
    f: Callable[[E], U],
) -> Result[T, U]:
    match r:
        case Ok():
            return r
        case Err(error=e):
            return Err(f(e))
