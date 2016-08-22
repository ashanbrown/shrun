# shrun

Yaml test flow runner

## Usage

Run commands shrun <file>.  Inspired by CircleCi's circle.yml files.

## Format

shrun expects a yaml file as input, with the top-level being a
"sequence."  

Note that in yaml, a number of symbols require quotation marks:

`{ } [ ] , & * # ? | - < > = ! % @ \)`

## Predicates

Commands can set predicates to control which lines are executed.

For example, you can use a predicate to determine whether you set up 
data in a cache:
```
-  "[ -d ~/cache ]":
    set: cached
- "mkdir -p ~/cache && do-something > ~/cache/file":
    unless: cached
```

## Parallelism

The simplest level of parallelism is to run a script in the
"background".  This can be used to capture examples indefinitely.

```
- "tail -f /var/log":
    background: true
```

Dependencies can be created between background jobs by giving them a
'name'.  Any 'named' are implicitly background processes.

```
- "curl https://host/file1 > file1":
    name: download_file1
- "curl https://host/file2 > file1":
    name: download_file2
- "tail -f /var/log":
    depends_on: download_file1 download_file2
```

Dependencies can be specified as yaml sequences or a single string of
whitespace delimited strings.

## Retries

Commands can be retried a given number of times at a given interval:

```
- "[ -e file ] || { touch file; false; }":
    interval: 5
    retries: 1
```

## Groups

Commands can be run for each member of a group:

```
- touch file_{{A,B}}
```

Groups can be used in names:


```
- sleep 10; touch file_{{A,B}}:
    name: name_{{A,B}}
- echo Done:
    depends_on: name_A name_B
```

Identical groups are replicated together, so

```
- touch file_{{A,B}}; mv file_{{A,B}} dir
```

becomes

```
- touch file_A; mv file_A dir
- touch file_B; mv file_B dir
```

Groups can be labeled to avoid having to repeat the content of the group:

Identical groups are replicated together, so

```
- touch file_{{my_group=A,B}}; mv file_{{my_group}} dir
```

also becomes

```
- touch file_A; mv file_A dir
- touch file_B; mv file_B dir
```

Labeled groups can be mapped to different values using a 1-1 mapping:

```
- mv file_{{my_group:A,B}} dir{{my_group:1,2}}
```

## Repeated Sequences

Repeated sequences of commands can be created similar to groups.  The first item
 in the sequence must have the repeat property set to a valid group specification.
 
```
- - foreach: my_group=A,B
  - touch file1_{{my_group}}
  - cp file1_{{my_group}} file2_{{my_group}}
```

Sequences can be nested:
 
```
- - foreach: my_group=A,B
  - - foreach: 1,2 
    - touch file1_{{my_group}}_{1,2}
```
