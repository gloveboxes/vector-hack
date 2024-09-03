--
-- PostgreSQL database dump
--

-- Dumped from database version 16.3 (Debian 16.3-1.pgdg120+1)
-- Dumped by pg_dump version 16.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: get_similar_videos(public.vector, double precision, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_similar_videos(query_vector public.vector, max_distance double precision, limit_count integer) RETURNS TABLE(speaker character varying, title character varying, description character varying, videoid character varying, seconds integer, text character varying, distance double precision)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        vc.speaker, 
        vc.title, 
        vc.description, 
        vc.videoid, 
        ve.seconds, 
        ve.text, 
        ve.embedding <=> query_vector AS distance
    FROM public.video_embeddings ve
    JOIN public.video_catalog vc ON ve.id = vc.id
    WHERE ve.embedding <=> query_vector < max_distance
    ORDER BY distance
    LIMIT limit_count;
END;
$$;


ALTER FUNCTION public.get_similar_videos(query_vector public.vector, max_distance double precision, limit_count integer) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: video_catalog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.video_catalog (
    id integer NOT NULL,
    speaker character varying(256) NOT NULL,
    title character varying(256) NOT NULL,
    description character varying(4096) NOT NULL,
    videoid character varying(128) NOT NULL
);


ALTER TABLE public.video_catalog OWNER TO postgres;

--
-- Name: video_embeddings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.video_embeddings (
    id bigint NOT NULL,
    embedding public.vector(768) NOT NULL,
    start character varying(64) NOT NULL,
    seconds integer NOT NULL,
    text character varying(12288) NOT NULL,
    summary character varying(16384) NOT NULL
);


ALTER TABLE public.video_embeddings OWNER TO postgres;

--
-- Name: video_gpt_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.video_gpt_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.video_gpt_id_seq OWNER TO postgres;

--
-- Name: video_gpt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.video_gpt_id_seq OWNED BY public.video_embeddings.id;


--
-- Name: video_embeddings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.video_embeddings ALTER COLUMN id SET DEFAULT nextval('public.video_gpt_id_seq'::regclass);


--
-- Name: video_embeddings video_gpt_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.video_embeddings
    ADD CONSTRAINT video_gpt_pkey PRIMARY KEY (id);


--
-- Name: video_catalog video_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.video_catalog
    ADD CONSTRAINT video_pkey PRIMARY KEY (id);


--
-- Name: video_embeddings fk_video_catalog_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.video_embeddings
    ADD CONSTRAINT fk_video_catalog_id FOREIGN KEY (id) REFERENCES public.video_catalog(id);


--
-- PostgreSQL database dump complete
--

