{
  "family": "romance",
  "version": "1.0",
  "languages": {
    "fr": {
      "language_code": "fr",
      "name": "French",
      "articles": {
        "definite": {
          "m": {
            "sg": "le",
            "pl": "les"
          },
          "f": {
            "sg": "la",
            "pl": "les"
          }
        },
        "indefinite": {
          "m": {
            "sg": "un",
            "pl": "des"
          },
          "f": {
            "sg": "une",
            "pl": "des"
          }
        },
        "elision": {
          "enabled": true,
          "vowel_onset_chars": ["a", "e", "i", "o", "u", "y", "h"],
          "definite_singular_forms": ["le", "la"],
          "elided_form": "l'"
        }
      },
      "nouns": {
        "gender_by_suffix": [
          { "suffix": "tion", "gender": "f" },
          { "suffix": "sion", "gender": "f" },
          { "suffix": "té", "gender": "f" },
          { "suffix": "ette", "gender": "f" },
          { "suffix": "ure", "gender": "f" },
          { "suffix": "age", "gender": "m" },
          { "suffix": "isme", "gender": "m" },
          { "suffix": "ment", "gender": "m" },
          { "suffix": "oir", "gender": "m" },
          { "suffix": "eau", "gender": "m" },
          { "suffix": "e", "gender": "f", "default": true }
        ],
        "pluralization": {
          "rules": [
            {
              "id": "al_aux",
              "if_endswith": "al",
              "replace_suffix": "aux"
            },
            {
              "id": "eau_x",
              "if_endswith": "eau",
              "add": "x"
            },
            {
              "id": "eu_x",
              "if_endswith": "eu",
              "add": "x"
            },
            {
              "id": "x_s_z_invariant",
              "if_endswith_one_of": ["x", "s", "z"],
              "keep": true
            },
            {
              "id": "default_add_s",
              "default": true,
              "add": "s"
            }
          ]
        },
        "feminization": {
          "rules": [
            {
              "id": "eur_euse",
              "if_endswith": "eur",
              "replace_suffix": "euse"
            },
            {
              "id": "ien_ienne",
              "if_endswith": "ien",
              "replace_suffix": "ienne"
            },
            {
              "id": "teur_trice",
              "if_endswith": "teur",
              "replace_suffix": "trice"
            },
            {
              "id": "on_onne",
              "if_endswith": "on",
              "add": "ne"
            },
            {
              "id": "en_enne",
              "if_endswith": "en",
              "add": "ne"
            },
            {
              "id": "default_add_e",
              "default": true,
              "add": "e"
            }
          ]
        }
      },
      "adjectives": {
        "position": "postnominal_default",
        "feminization_rules": [
          {
            "id": "eux_euse",
            "if_endswith": "eux",
            "replace_suffix": "euse"
          },
          {
            "id": "if_endswith_er_ere",
            "if_endswith": "er",
            "replace_suffix": "ère"
          },
          {
            "id": "if_endswith_en_enne",
            "if_endswith": "en",
            "add": "ne"
          },
          {
            "id": "default_add_e",
            "default": true,
            "add": "e"
          }
        ],
        "pluralization_rules": [
          {
            "id": "x_s_z_invariant",
            "if_endswith_one_of": ["x", "s", "z"],
            "keep": true
          },
          {
            "id": "default_add_s",
            "default": true,
            "add": "s"
          }
        ]
      },
      "phonology": {
        "impure_s_onset": {
          "enabled": true,
          "patterns": ["sp", "st", "sc", "sk"]
        }
      },
      "order": {
        "basic_word_order": "SVO",
        "adverbial_position": "final",
        "adjective_position": {
          "default": "postnominal",
          "exceptions_pre": ["grand", "petit", "jeune", "vieux", "beau", "joli", "bon", "mauvais"]
        }
      },
      "lexicon": {
        "irregular_nouns": {
          "oeil": {
            "gender": "m",
            "number=sg": "oeil",
            "number=pl": "yeux"
          },
          "pays": {
            "gender": "m",
            "number=sg": "pays",
            "number=pl": "pays"
          }
        },
        "irregular_adjectives": {
          "beau": {
            "base": "beau",
            "masc_sg": "beau",
            "masc_sg_before_vowel": "bel",
            "fem_sg": "belle",
            "masc_pl": "beaux",
            "fem_pl": "belles"
          }
        }
      }
    },
    "it": {
      "language_code": "it",
      "name": "Italian",
      "articles": {
        "definite": {
          "m": {
            "sg": {
              "default": "il",
              "before_vowel": "l'",
              "before_z_s_impure": "lo"
            },
            "pl": {
              "default": "i",
              "before_vowel": "gli",
              "before_z_s_impure": "gli"
            }
          },
          "f": {
            "sg": {
              "default": "la",
              "before_vowel": "l'"
            },
            "pl": {
              "default": "le"
            }
          }
        },
        "indefinite": {
          "m": {
            "sg": {
              "default": "un",
              "before_z_s_impure": "uno"
            }
          },
          "f": {
            "sg": {
              "default": "una",
              "before_vowel": "un'"
            }
          }
        },
        "z_s_impure_onset": {
          "enabled": true,
          "patterns": ["z", "s", "ps", "gn", "x"]
        }
      },
      "nouns": {
        "gender_by_suffix": [
          { "suffix": "a", "gender": "f" },
          { "suffix": "o", "gender": "m" },
          { "suffix": "e", "gender": "m" }
        ],
        "pluralization": {
          "rules": [
            {
              "id": "o_to_i",
              "if_endswith": "o",
              "replace_suffix": "i"
            },
            {
              "id": "a_to_e",
              "if_endswith": "a",
              "replace_suffix": "e"
            },
            {
              "id": "e_to_i",
              "if_endswith": "e",
              "replace_suffix": "i"
            },
            {
              "id": "accented_invariant",
              "if_endswith_one_of": ["à", "è", "é", "ì", "ò", "ù"],
              "keep": true
            },
            {
              "id": "consonant_invariant",
              "if_final_is_consonant": true,
              "keep": true
            }
          ]
        },
        "feminization": {
          "rules": [
            {
              "id": "ore_trice",
              "if_endswith": "ore",
              "replace_suffix": "trice"
            },
            {
              "id": "ore_ora",
              "if_endswith": "ore_alt",
              "replace_suffix": "ora"
            },
            {
              "id": "o_a",
              "if_endswith": "o",
              "replace_suffix": "a"
            },
            {
              "id": "default",
              "default": true,
              "add": "a"
            }
          ]
        }
      },
      "adjectives": {
        "position": "postnominal_default",
        "classes": {
          "2_class": {
            "o_to_i_a_to_e": true
          },
          "1_class": {
            "e_to_i": true
          }
        },
        "feminization_rules": [
          {
            "id": "o_to_a",
            "if_endswith": "o",
            "replace_suffix": "a"
          },
          {
            "id": "e_invariant_fem",
            "if_endswith": "e",
            "keep": true
          }
        ],
        "pluralization_rules": [
          {
            "id": "adj_o_to_i",
            "if_endswith": "o",
            "replace_suffix": "i"
          },
          {
            "id": "adj_a_to_e",
            "if_endswith": "a",
            "replace_suffix": "e"
          },
          {
            "id": "adj_e_to_i",
            "if_endswith": "e",
            "replace_suffix": "i"
          }
        ]
      },
      "phonology": {
        "z_s_impure": {
          "enabled": true,
          "patterns": ["z", "s", "ps", "gn", "x"]
        }
      },
      "order": {
        "basic_word_order": "SVO",
        "adverbial_position": "final",
        "adjective_position": {
          "default": "postnominal",
          "stylistic_pre": true
        }
      },
      "lexicon": {
        "irregular_nouns": {
          "uomo": {
            "gender": "m",
            "number=sg": "uomo",
            "number=pl": "uomini"
          },
          "braccio": {
            "gender": "m",
            "number=sg": "braccio",
            "number=pl": "braccia"
          }
        }
      }
    },
    "es": {
      "language_code": "es",
      "name": "Spanish",
      "articles": {
        "definite": {
          "m": {
            "sg": "el",
            "pl": "los"
          },
          "f": {
            "sg": "la",
            "pl": "las"
          }
        },
        "indefinite": {
          "m": {
            "sg": "un",
            "pl": "unos"
          },
          "f": {
            "sg": "una",
            "pl": "unas"
          }
        },
        "a_to_ha_tonic": {
          "enabled": true,
          "trigger_vowels": ["a"],
          "special_nouns": ["águila", "agua", "alma"]
        }
      },
      "nouns": {
        "gender_by_suffix": [
          { "suffix": "a", "gender": "f" },
          { "suffix": "o", "gender": "m" },
          { "suffix": "dad", "gender": "f" },
          { "suffix": "ción", "gender": "f" },
          { "suffix": "tud", "gender": "f" },
          { "suffix": "ma", "gender": "m" }
        ],
        "pluralization": {
          "rules": [
            {
              "id": "vowel_add_s",
              "if_final_is_vowel": true,
              "add": "s"
            },
            {
              "id": "z_to_ces",
              "if_endswith": "z",
              "replace_suffix": "ces"
            },
            {
              "id": "consonant_add_es",
              "if_final_is_consonant": true,
              "add": "es"
            }
          ]
        },
        "feminization": {
          "rules": [
            {
              "id": "o_to_a",
              "if_endswith": "o",
              "replace_suffix": "a"
            },
            {
              "id": "or_ora",
              "if_endswith": "or",
              "add": "a"
            },
            {
              "id": "án_ana",
              "if_endswith": "án",
              "replace_suffix": "ana"
            },
            {
              "id": "default_add_a",
              "default": true,
              "add": "a"
            }
          ]
        }
      },
      "adjectives": {
        "position": "postnominal_default",
        "feminization_rules": [
          {
            "id": "adj_o_to_a",
            "if_endswith": "o",
            "replace_suffix": "a"
          },
          {
            "id": "adj_e_invariant_fem",
            "if_endswith": "e",
            "keep": true
          }
        ],
        "pluralization_rules": [
          {
            "id": "adj_vowel_add_s",
            "if_final_is_vowel": true,
            "add": "s"
          },
          {
            "id": "adj_consonant_add_es",
            "if_final_is_consonant": true,
            "add": "es"
          }
        ]
      },
      "phonology": {
        "unstressed_vowel_drop": {
          "enabled": false
        }
      },
      "order": {
        "basic_word_order": "SVO",
        "adverbial_position": "final",
        "adjective_position": {
          "default": "postnominal",
          "semantic_pre_for": ["grande", "pobre", "antiguo"]
        }
      },
      "lexicon": {
        "irregular_nouns": {
          "mano": {
            "gender": "f",
            "number=sg": "mano",
            "number=pl": "manos"
          }
        }
      }
    },
    "pt": {
      "language_code": "pt",
      "name": "Portuguese",
      "articles": {
        "definite": {
          "m": {
            "sg": "o",
            "pl": "os"
          },
          "f": {
            "sg": "a",
            "pl": "as"
          }
        },
        "indefinite": {
          "m": {
            "sg": "um",
            "pl": "uns"
          },
          "f": {
            "sg": "uma",
            "pl": "umas"
          }
        }
      },
      "nouns": {
        "gender_by_suffix": [
          { "suffix": "o", "gender": "m" },
          { "suffix": "a", "gender": "f" },
          { "suffix": "dade", "gender": "f" },
          { "suffix": "ção", "gender": "f" }
        ],
        "pluralization": {
          "rules": [
            {
              "id": "vowel_add_s",
              "if_final_is_vowel": true,
              "add": "s"
            },
            {
              "id": "m_to_ns",
              "if_endswith": "m",
              "replace_suffix": "ns"
            },
            {
              "id": "l_to_is",
              "if_endswith": "l",
              "replace_suffix": "is"
            }
          ]
        },
        "feminization": {
          "rules": [
            {
              "id": "o_to_a",
              "if_endswith": "o",
              "replace_suffix": "a"
            },
            {
              "id": "or_ora",
              "if_endswith": "or",
              "add": "a"
            },
            {
              "id": "default",
              "default": true,
              "add": "a"
            }
          ]
        }
      },
      "adjectives": {
        "position": "postnominal_default",
        "feminization_rules": [
          {
            "id": "adj_o_to_a",
            "if_endswith": "o",
            "replace_suffix": "a"
          },
          {
            "id": "adj_e_invariant_fem",
            "if_endswith": "e",
            "keep": true
          }
        ],
        "pluralization_rules": [
          {
            "id": "adj_vowel_add_s",
            "if_final_is_vowel": true,
            "add": "s"
          },
          {
            "id": "adj_m_to_ns",
            "if_endswith": "m",
            "replace_suffix": "ns"
          }
        ]
      },
      "phonology": {
        "nasal_vowels": {
          "enabled": true
        }
      },
      "order": {
        "basic_word_order": "SVO",
        "adverbial_position": "final"
      },
      "lexicon": {
        "irregular_nouns": {}
      }
    },
    "ro": {
      "language_code": "ro",
      "name": "Romanian",
      "articles": {
        "definite": {
          "m": {
            "sg_suffix": "ul",
            "pl_suffix": "i"
          },
          "f": {
            "sg_suffix": "a",
            "pl_suffix": "le"
          },
          "n": {
            "sg_suffix": "ul",
            "pl_suffix": "e"
          }
        },
        "indefinite": {
          "m": {
            "sg": "un",
            "pl": "niște"
          },
          "f": {
            "sg": "o",
            "pl": "niște"
          }
        },
        "definite_is_enclitic": true
      },
      "nouns": {
        "gender_by_suffix": [
          { "suffix": "ă", "gender": "f" },
          { "suffix": "a", "gender": "f" },
          { "suffix": "e", "gender": "f" },
          { "suffix": "e", "gender": "n" },
          { "suffix": "u", "gender": "m" }
        ],
        "pluralization": {
          "rules": [
            {
              "id": "a_to_e",
              "if_endswith": "ă",
              "replace_suffix": "e"
            },
            {
              "id": "e_to_e",
              "if_endswith": "e",
              "keep": true
            },
            {
              "id": "generic_i",
              "default": true,
              "add": "i"
            }
          ]
        },
        "feminization": {
          "rules": [
            {
              "id": "generic_add_ă",
              "default": true,
              "add": "ă"
            }
          ]
        }
      },
      "adjectives": {
        "position": "postnominal_default",
        "agreement": {
          "gender": true,
          "number": true
        }
      },
      "phonology": {
        "palatalization": {
          "enabled": false
        }
      },
      "order": {
        "basic_word_order": "SVO",
        "adverbial_position": "final"
      },
      "lexicon": {
        "irregular_nouns": {}
      }
    }
  }
}
