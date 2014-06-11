---
--- avrc_data/visit_cycle -> pirc/visit_cycle
---

DROP FOREIGN TABLE IF EXISTS visit_cycle_ext;


CREATE FOREIGN TABLE visit_cycle_ext (
    visit_id        INTEGER NOT NULL
  , cycle_id        INTEGER NOT NULL
)
SERVER trigger_target
OPTIONS (table_name 'visit_cycle');


CREATE OR REPLACE FUNCTION visit_cycle_mirror() RETURNS TRIGGER AS $$
  BEGIN
    CASE TG_OP
      WHEN 'INSERT' THEN
        INSERT INTO visit_cycle_ext VALUES (
            ext_visit_id(NEW.visit_id)
          , ext_cycle_id(NEW.cycle_id)
          );
        RETURN NEW;
      WHEN 'DELETE' THEN
        DELETE
        FROM visit_cycle_ext
        WHERE visit_id = (SELECT * FROM ext_visit_id(OLD.visit_id))
          AND cycle_id = (SELECT * FROM ext_cycle_id(OLD.cycle_id));
        RETURN OLD;
      WHEN 'UPDATE' THEN
        UPDATE visit_cycle_ext
        SET visit_id = ext_visit_id(NEW.visit_id)
          , cycle_id = ext_cycle_id(NEW.cycle_id)
        WHERE visit_id = (SELECT * FROM ext_visit_id(OLD.visit_id))
          AND cycle_id = (SELECT * FROM ext_cycle_id(OLD.cycle_id));
        RETURN NEW;
    END CASE;
    RETURN NULL;
  END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS visit_cycle_mirror ON visit_cycle;


CREATE TRIGGER visit_cycle_mirror AFTER INSERT OR UPDATE OR DELETE ON visit_cycle
  FOR EACH ROW EXECUTE PROCEDURE visit_cycle_mirror();
