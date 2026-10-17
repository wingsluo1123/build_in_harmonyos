:- use_module(library(plunit)).
:- use_module(library(clpfd)).
:- use_module(library(http/json)).
:- use_module(library(pcre)).
:- use_module(library(yaml)).
:- use_module(library(crypto)).
:- use_module(library(zlib)).
:- use_module(library(archive)).
:- use_module(library(memfile)).
:- use_module(library(semweb/rdf_db)).
:- use_module(library(sgml)).
:- current_prolog_flag(argv, [Extension|_]), load_foreign_library(Extension).
:- table path/2.
edge(a,b).
edge(b,c).
path(X,Y) :- edge(X,Y).
path(X,Y) :- edge(X,Z), path(Z,Y).
:- dynamic shared_value/1.

:- begin_tests(ohos_consumer).
test(version) :- current_prolog_flag(version_data, swi(10,0,2,_)).
test(architecture) :- current_prolog_flag(arch, 'aarch64-ohos').
test(integer) :- X is 2^200, X =:= 1606938044258990275541962092341162602522202993782792835301376.
test(rational) :- X is 1 rdiv 3, 3*X =:= 1.
test(unicode) :- atom_codes('鸿蒙', [40511,33945]).
test(dcg) :- phrase(([a], [b]), [a,b]).
test(tabling, set(Y == [b,c])) :- path(a,Y).
test(constraints, all(X == [1,2,3])) :- X in 1..3, label([X]).
test(dict) :- D = point{x:3,y:4}, get_dict(x,D,3), D.y =:= 4.
test(json) :- atom_json_dict('{"name":"ohos","n":42}', D, []), D.n =:= 42.
test(regex) :- re_matchsub('(?<name>[a-z]+)(?<n>[0-9]+)', 'ohos42', D, []), D.name == "ohos", D.n == "42".
test(yaml) :- yaml_read(string("name: ohos\nn: 42\n"), D), D.n =:= 42.
test(sha256) :- crypto_data_hash(abc, H, [algorithm(sha256)]), H == ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad.
test(engine) :- engine_create(X, member(X,[a,b]), E), engine_next(E,a), engine_next(E,b), \+ engine_next(E,_), engine_destroy(E).
test(thread) :- thread_create(true, Id, []), thread_join(Id,true).
test(thread_reuse) :- forall(between(1,1000,_), (thread_create(true,Id,[]), thread_join(Id,true))).
test(engine_owner_thread) :-
    native_altstack_token(Before), Before > 0,
    forall(between(1,100,_),
        ( engine_create(_,true,Engine), native_altstack_token(Before),
          thread_create(engine_destroy(Engine),Id,[]), thread_join(Id,true),
          native_altstack_token(Before) )).
test(message_queue) :- setup_call_cleanup(message_queue_create(Q), (thread_send_message(Q, hello(42)), thread_get_message(Q, hello(42))), message_queue_destroy(Q)).
test(mutex) :- with_mutex(ohos_lock, (assertz(shared_value(42)), retract(shared_value(42)))).
test(transaction) :- transaction(assertz(shared_value(7))), retract(shared_value(7)).
test(exception, throws(error(type_error(integer, atom),_))) :- native_sum(atom,1,_).
test(foreign) :- native_sum(20,22,42).
test(gc) :- forall(between(1,1000,_), (length(L,100), L=[_|_])), garbage_collect.
test(atom_gc) :- atom_concat(harmony,os,harmonyos), garbage_collect_atoms.
test(memory_file) :- setup_call_cleanup(new_memory_file(M), (setup_call_cleanup(open_memory_file(M,write,S), write(S,hello), close(S)), memory_file_to_atom(M,hello)), free_memory_file(M)).
test(rdf) :- rdf_assert('urn:s','urn:p',literal(ohos)), rdf('urn:s','urn:p',literal(ohos)), rdf_retractall('urn:s',_,_).
test(xml) :- setup_call_cleanup(open_string('<root><n>42</n></root>',S), load_structure(S,[element(root,[],[element(n,[],['42'])])],[dialect(xml)]),close(S)).
test(gzip) :- tmp_file(ohos_gzip,F), setup_call_cleanup(true, (setup_call_cleanup(gzopen(F,write,S),write(S,hello),close(S)), setup_call_cleanup(gzopen(F,read,R),read_string(R,_,"hello"),close(R))),delete_file(F)).
test(archive) :-
    tmp_file(ohos_tar, Tar), tmp_file(ohos_member, Member),
    setup_call_cleanup(true,
        ( setup_call_cleanup(open(Member,write,S), write(S,hello), close(S)),
          archive_create(Tar,[Member],[format(gnutar)]),
          setup_call_cleanup(archive_open(Tar,read,A,[]),
            ( archive_next_header(A,_),
              setup_call_cleanup(archive_open_entry(A,R), read_string(R,_,"hello"), close(R)) ),
            archive_close(A)) ),
        (delete_file(Tar),delete_file(Member))).
:- end_tests(ohos_consumer).
