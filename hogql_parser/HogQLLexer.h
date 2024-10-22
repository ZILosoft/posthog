
// Generated from HogQLLexer.g4 by ANTLR 4.13.2

#pragma once


#include "antlr4-runtime.h"




class  HogQLLexer : public antlr4::Lexer {
public:
  enum {
    ALL = 1, AND = 2, ANTI = 3, ANY = 4, ARRAY = 5, AS = 6, ASCENDING = 7, 
    ASOF = 8, BETWEEN = 9, BOTH = 10, BY = 11, CASE = 12, CAST = 13, CATCH = 14, 
    COHORT = 15, COLLATE = 16, CROSS = 17, CUBE = 18, CURRENT = 19, DATE = 20, 
    DAY = 21, DESC = 22, DESCENDING = 23, DISTINCT = 24, ELSE = 25, END = 26, 
    EXTRACT = 27, FINAL = 28, FINALLY = 29, FIRST = 30, FN = 31, FOLLOWING = 32, 
    FOR = 33, FROM = 34, FULL = 35, FUN = 36, GROUP = 37, HAVING = 38, HOUR = 39, 
    ID = 40, IF = 41, ILIKE = 42, IN = 43, INF = 44, INNER = 45, INTERSECT = 46, 
    INTERVAL = 47, IS = 48, JOIN = 49, KEY = 50, LAST = 51, LEADING = 52, 
    LEFT = 53, LET = 54, LIKE = 55, LIMIT = 56, MINUTE = 57, MONTH = 58, 
    NAN_SQL = 59, NOT = 60, NULL_SQL = 61, NULLS = 62, OFFSET = 63, ON = 64, 
    OR = 65, ORDER = 66, OUTER = 67, OVER = 68, PARTITION = 69, PRECEDING = 70, 
    PREWHERE = 71, QUARTER = 72, RANGE = 73, RETURN = 74, RIGHT = 75, ROLLUP = 76, 
    ROW = 77, ROWS = 78, SAMPLE = 79, SECOND = 80, SELECT = 81, SEMI = 82, 
    SETTINGS = 83, SUBSTRING = 84, THEN = 85, THROW = 86, TIES = 87, TIMESTAMP = 88, 
    TO = 89, TOP = 90, TOTALS = 91, TRAILING = 92, TRIM = 93, TRUNCATE = 94, 
    TRY = 95, UNBOUNDED = 96, UNION = 97, USING = 98, WEEK = 99, WHEN = 100, 
    WHERE = 101, WHILE = 102, WINDOW = 103, WITH = 104, YEAR = 105, ESCAPE_CHAR_COMMON = 106, 
    IDENTIFIER = 107, FLOATING_LITERAL = 108, OCTAL_LITERAL = 109, DECIMAL_LITERAL = 110, 
    HEXADECIMAL_LITERAL = 111, STRING_LITERAL = 112, ARROW = 113, ASTERISK = 114, 
    BACKQUOTE = 115, BACKSLASH = 116, COLON = 117, COMMA = 118, CONCAT = 119, 
    DASH = 120, DOLLAR = 121, DOT = 122, EQ_DOUBLE = 123, EQ_SINGLE = 124, 
    GT_EQ = 125, GT = 126, HASH = 127, IREGEX_SINGLE = 128, IREGEX_DOUBLE = 129, 
    LBRACE = 130, LBRACKET = 131, LPAREN = 132, LT_EQ = 133, LT = 134, NOT_EQ = 135, 
    NOT_IREGEX = 136, NOT_REGEX = 137, NULL_PROPERTY = 138, NULLISH = 139, 
    PERCENT = 140, PLUS = 141, QUERY = 142, QUOTE_DOUBLE = 143, QUOTE_SINGLE_TEMPLATE = 144, 
    QUOTE_SINGLE_TEMPLATE_FULL = 145, QUOTE_SINGLE = 146, REGEX_SINGLE = 147, 
    REGEX_DOUBLE = 148, RBRACE = 149, RBRACKET = 150, RPAREN = 151, SEMICOLON = 152, 
    SLASH = 153, UNDERSCORE = 154, MULTI_LINE_COMMENT = 155, SINGLE_LINE_COMMENT = 156, 
    WHITESPACE = 157, STRING_TEXT = 158, STRING_ESCAPE_TRIGGER = 159, FULL_STRING_TEXT = 160, 
    FULL_STRING_ESCAPE_TRIGGER = 161
  };

  enum {
    IN_TEMPLATE_STRING = 1, IN_FULL_TEMPLATE_STRING = 2
  };

  explicit HogQLLexer(antlr4::CharStream *input);

  ~HogQLLexer() override;


  std::string getGrammarFileName() const override;

  const std::vector<std::string>& getRuleNames() const override;

  const std::vector<std::string>& getChannelNames() const override;

  const std::vector<std::string>& getModeNames() const override;

  const antlr4::dfa::Vocabulary& getVocabulary() const override;

  antlr4::atn::SerializedATNView getSerializedATN() const override;

  const antlr4::atn::ATN& getATN() const override;

  // By default the static state used to implement the lexer is lazily initialized during the first
  // call to the constructor. You can call this function if you wish to initialize the static state
  // ahead of time.
  static void initialize();

private:

  // Individual action functions triggered by action() above.

  // Individual semantic predicate functions triggered by sempred() above.

};

